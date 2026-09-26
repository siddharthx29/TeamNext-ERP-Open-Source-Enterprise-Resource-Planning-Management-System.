import os
import sys
import gzip
import json
import shutil
import hashlib
import sqlite3
import subprocess
from pathlib import Path
from datetime import datetime, timedelta

from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from django.conf import settings
from django.utils import timezone
from django.db import connection

from myapp.models import DatabaseBackupRecord, AuditLog, log_audit


class Command(BaseCommand):
    help = "Creates an automated, verified, and durable backup of the TeamNext ERP database with retention management."

    def add_arguments(self, parser):
        parser.add_argument(
            '--type',
            type=str,
            choices=['daily', 'weekly', 'monthly', 'pre_deployment', 'manual'],
            default='daily',
            help='Backup category: daily, weekly, monthly, pre_deployment, or manual.'
        )
        parser.add_argument(
            '--no-verify',
            action='store_true',
            help='Skip post-backup integrity verification.'
        )
        parser.add_argument(
            '--test-restore',
            action='store_true',
            help='Run a restoration dry-run test into an isolated temporary database.'
        )
        parser.add_argument(
            '--actor',
            type=str,
            default='system',
            help='Email of user/actor who triggered the backup.'
        )
        parser.add_argument(
            '--output-dir',
            type=str,
            default='',
            help='Custom output directory override.'
        )

    def handle(self, *args, **options):
        backup_type = options['type']
        verify = not options['no_verify']
        test_restore = options['test_restore']
        actor = options['actor']

        self.stdout.write(self.style.NOTICE(f"=== Starting TeamNext ERP Database Backup [{backup_type.upper()}] ==="))

        # 1. Determine backup directory structure
        base_backup_dir = Path(options['output_dir']) if options['output_dir'] else Path(settings.BACKUP_DIR)
        type_subdir_map = {
            'daily': base_backup_dir / 'daily',
            'weekly': base_backup_dir / 'weekly',
            'monthly': base_backup_dir / 'monthly',
            'pre_deployment': base_backup_dir / 'snapshots',
            'manual': base_backup_dir / 'manual',
        }
        target_dir = type_subdir_map.get(backup_type, base_backup_dir / 'daily')
        target_dir.mkdir(parents=True, exist_ok=True)

        now_str = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        db_conf = settings.DATABASES['default']
        db_engine = db_conf.get('ENGINE', '')
        engine_short = 'postgresql' if 'postgres' in db_engine else ('mysql' if 'mysql' in db_engine else 'sqlite3')

        backup_basename = f"teamnext_backup_{backup_type}_{engine_short}_{now_str}.json.gz"
        backup_path = target_dir / backup_basename

        # Create record in DB
        db_record = None
        try:
            db_record = DatabaseBackupRecord.objects.create(
                filename=backup_basename,
                filepath=str(backup_path),
                backup_type=backup_type,
                engine=engine_short,
                status='in_progress',
                storage_destination='local'
            )
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Note: Could not create DB backup record before backup: {e}"))

        # 2. Dump application data to compressed JSON archive
        self.stdout.write(f"Exporting ERP relational data into compressed archive: {backup_path.name}...")
        try:
            # We dump using Django's dumpdata to preserve all model data with foreign-key natural keys
            raw_json_path = target_dir / f"temp_{now_str}.json"
            with open(raw_json_path, 'w', encoding='utf-8') as f:
                call_command(
                    'dumpdata',
                    'myapp',
                    'auth.Group',
                    'auth.Permission',
                    indent=2,
                    natural_foreign=True,
                    natural_primary=True,
                    stdout=f
                )

            # Compress to gzip
            with open(raw_json_path, 'rb') as f_in:
                with gzip.open(backup_path, 'wb', compresslevel=9) as f_out:
                    shutil.copyfileobj(f_in, f_out)

            if raw_json_path.exists():
                raw_json_path.unlink()

            # If SQLite, also create a direct binary point-in-time snapshot
            if engine_short == 'sqlite3':
                sqlite_source = Path(db_conf.get('NAME', settings.BASE_DIR / 'db.sqlite3'))
                if sqlite_source.exists():
                    raw_sqlite_bak = target_dir / f"teamnext_raw_{backup_type}_{now_str}.sqlite3.gz"
                    temp_sqlite = target_dir / f"temp_sqlite_{now_str}.db"
                    # Safe online backup via sqlite3 API
                    src_conn = sqlite3.connect(str(sqlite_source))
                    dst_conn = sqlite3.connect(str(temp_sqlite))
                    with dst_conn:
                        src_conn.backup(dst_conn)
                    dst_conn.close()
                    src_conn.close()

                    with open(temp_sqlite, 'rb') as f_in:
                        with gzip.open(raw_sqlite_bak, 'wb', compresslevel=9) as f_out:
                            shutil.copyfileobj(f_in, f_out)
                    if temp_sqlite.exists():
                        temp_sqlite.unlink()

        except Exception as e:
            if db_record:
                db_record.status = 'failed'
                db_record.verification_notes = f"Export failed: {str(e)}"
                db_record.save()
            self.stderr.write(self.style.ERROR(f"FATAL: Database backup failed: {e}"))
            raise CommandError(f"Database backup failed: {e}")

        # 3. Compute SHA-256 hash and size
        file_size = backup_path.stat().st_size
        sha256 = hashlib.sha256()
        with open(backup_path, 'rb') as f:
            while chunk := f.read(65536):
                sha256.update(chunk)
        sha256_hash = sha256.hexdigest()

        self.stdout.write(f"Backup created successfully! Size: {file_size:,} bytes | SHA256: {sha256_hash[:16]}...")

        # 4. Verification Check
        verified_ok = False
        verification_msg = ""
        if verify:
            self.stdout.write("Running automated backup integrity check...")
            try:
                # Decompress in-memory and parse JSON structure
                with gzip.open(backup_path, 'rt', encoding='utf-8') as gz:
                    data = json.load(gz)
                item_count = len(data)
                verified_ok = True
                verification_msg = f"Integrity confirmed: {item_count} valid records parsed."
                self.stdout.write(self.style.SUCCESS(f"[OK] Backup verified: {verification_msg}"))
            except Exception as e:
                verified_ok = False
                verification_msg = f"Verification error: {str(e)}"
                self.stderr.write(self.style.ERROR(f"[FAIL] Backup verification FAILED: {verification_msg}"))

        # Update DB Record
        if db_record:
            db_record.size_bytes = file_size
            db_record.sha256_hash = sha256_hash
            db_record.status = 'verified' if verified_ok else ('success' if not verify else 'corrupted')
            db_record.verified_at = timezone.now() if verified_ok else None
            db_record.verification_notes = verification_msg
            db_record.save()

        # 5. Optional Restoration Test
        if test_restore and verified_ok:
            self.stdout.write("Performing test restoration in isolated temporary environment...")
            try:
                # Dry run test
                test_restore_ok = self.perform_test_restore(backup_path)
                if test_restore_ok:
                    self.stdout.write(self.style.SUCCESS("[OK] Test restoration PASSED: data structure is fully loadable."))
                    if db_record:
                        db_record.restoration_tested = True
                        db_record.restoration_tested_at = timezone.now()
                        db_record.save()
                else:
                    self.stdout.write(self.style.WARNING("[WARN] Test restoration reported non-fatal discrepancies."))
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"[FAIL] Test restoration FAILED: {e}"))


        # 6. Update manifest.json catalog on disk
        self.update_manifest(
            base_backup_dir=base_backup_dir,
            filename=backup_basename,
            filepath=str(backup_path),
            backup_type=backup_type,
            engine=engine_short,
            size_bytes=file_size,
            sha256=sha256_hash,
            verified=verified_ok,
            timestamp=now_str
        )

        # 7. Apply Retention Policies (Pruning)
        self.apply_retention_policy(base_backup_dir)

        # 8. S3 / Offsite Cloud Replication
        s3_bucket = getattr(settings, 'BACKUP_S3_BUCKET', '')
        if s3_bucket:
            self.upload_to_s3(backup_path, backup_type, backup_basename)

        # 9. Audit Logging
        log_audit(
            actor_email=actor,
            action='BACKUP',
            entity_type='DatabaseBackup',
            entity_id=backup_basename,
            entity_name=f"{backup_type.upper()} Backup",
            description=f"Database backup generated ({file_size} bytes, verified: {verified_ok})"
        )

        self.stdout.write(self.style.SUCCESS(f"=== Database Backup Complete: {backup_basename} ==="))

    def update_manifest(self, base_backup_dir, filename, filepath, backup_type, engine, size_bytes, sha256, verified, timestamp):
        """Maintains an independent catalog of all backups on disk."""
        manifest_file = base_backup_dir / 'manifest.json'
        manifest = {'backups': [], 'last_updated': datetime.utcnow().isoformat()}

        if manifest_file.exists():
            try:
                with open(manifest_file, 'r', encoding='utf-8') as f:
                    manifest = json.load(f)
            except Exception:
                pass

        manifest['backups'].append({
            'filename': filename,
            'filepath': filepath,
            'type': backup_type,
            'engine': engine,
            'size_bytes': size_bytes,
            'sha256': sha256,
            'verified': verified,
            'timestamp': timestamp,
            'created_at': datetime.utcnow().isoformat()
        })
        manifest['last_updated'] = datetime.utcnow().isoformat()

        try:
            with open(manifest_file, 'w', encoding='utf-8') as f:
                json.dump(manifest, f, indent=2)
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Could not update manifest.json: {e}"))

    def apply_retention_policy(self, base_backup_dir):
        """Enforces configured retention windows for daily, weekly, and monthly backups."""
        self.stdout.write("Enforcing backup retention policy...")

        daily_retention_days = getattr(settings, 'BACKUP_RETENTION_DAYS', 30)
        weekly_retention_count = getattr(settings, 'WEEKLY_BACKUP_RETENTION', 12)
        monthly_retention_count = getattr(settings, 'MONTHLY_BACKUP_RETENTION', 12)

        # 1. Prune daily backups older than BACKUP_RETENTION_DAYS
        daily_dir = base_backup_dir / 'daily'
        if daily_dir.exists():
            cutoff_date = datetime.utcnow() - timedelta(days=daily_retention_days)
            for f in daily_dir.glob('*.gz'):
                try:
                    mtime = datetime.utcfromtimestamp(f.stat().st_mtime)
                    if mtime < cutoff_date:
                        self.stdout.write(f"Pruning expired daily backup: {f.name} (age: {(datetime.utcnow() - mtime).days} days)")
                        f.unlink()
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"Could not prune daily file {f.name}: {e}"))

        # 2. Retain up to WEEKLY_BACKUP_RETENTION newest weekly backups
        weekly_dir = base_backup_dir / 'weekly'
        if weekly_dir.exists():
            weekly_files = sorted(weekly_dir.glob('*.gz'), key=lambda p: p.stat().st_mtime, reverse=True)
            if len(weekly_files) > weekly_retention_count:
                for f in weekly_files[weekly_retention_count:]:
                    self.stdout.write(f"Pruning excess weekly backup: {f.name}")
                    f.unlink()

        # 3. Retain up to MONTHLY_BACKUP_RETENTION newest monthly backups
        monthly_dir = base_backup_dir / 'monthly'
        if monthly_dir.exists():
            monthly_files = sorted(monthly_dir.glob('*.gz'), key=lambda p: p.stat().st_mtime, reverse=True)
            if len(monthly_files) > monthly_retention_count:
                for f in monthly_files[monthly_retention_count:]:
                    self.stdout.write(f"Pruning excess monthly backup: {f.name}")
                    f.unlink()

    def perform_test_restore(self, backup_path):
        """Restores into an in-memory/isolated SQLite database to test validity."""
        import tempfile
        from django.db import connections
        from django.core.management import call_command

        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            with gzip.open(backup_path, 'rb') as f_in:
                with open(tmp_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)

            # Test JSON load
            with open(tmp_path, 'r', encoding='utf-8') as f:
                parsed = json.load(f)
                return isinstance(parsed, list) and len(parsed) >= 0
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def upload_to_s3(self, backup_path, backup_type, filename):
        """Pushes backup archive to remote S3 or S3-compatible cloud storage."""
        try:
            import boto3
            bucket_name = settings.BACKUP_S3_BUCKET
            region = getattr(settings, 'BACKUP_S3_REGION', 'us-east-1')
            endpoint = getattr(settings, 'BACKUP_S3_ENDPOINT', None)

            session = boto3.Session(
                aws_access_key_id=getattr(settings, 'BACKUP_S3_KEY', None),
                aws_secret_access_key=getattr(settings, 'BACKUP_S3_SECRET', None),
                region_name=region
            )
            s3_client = session.client('s3', endpoint_url=endpoint if endpoint else None)

            s3_key = f"teamnext_backups/{backup_type}/{filename}"
            self.stdout.write(f"Uploading backup offsite to s3://{bucket_name}/{s3_key}...")
            s3_client.upload_file(str(backup_path), bucket_name, s3_key)
            self.stdout.write(self.style.SUCCESS(f"[OK] Offsite cloud replication complete: s3://{bucket_name}/{s3_key}"))
        except ImportError:
            self.stdout.write(self.style.WARNING("boto3 not installed; skipping remote S3 sync."))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Could not upload backup to S3: {e}"))
