import os
import sys
import gzip
import json
import shutil
import hashlib
import tempfile
from pathlib import Path
from datetime import datetime

from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.conf import settings
from django.db import connection, transaction

from myapp.models import (
    Company, Employee, DatabaseBackupRecord, AuditLog, log_audit
)


class Command(BaseCommand):
    help = "Safely restores the TeamNext ERP database from a verified backup archive with pre-restore safety snapshots."

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='',
            help='Path to the backup archive (.json.gz or .sqlite3.gz) to restore.'
        )
        parser.add_argument(
            '--latest',
            action='store_true',
            help='Automatically restore the newest verified backup found in BACKUP_DIR.'
        )
        parser.add_argument(
            '--backup-id',
            type=int,
            default=0,
            help='DatabaseBackupRecord primary key ID to restore.'
        )
        parser.add_argument(
            '--confirm',
            type=str,
            default='',
            help='Confirmation flag. Must be set to "CONFIRM_RESTORE" to proceed in non-interactive mode.'
        )
        parser.add_argument(
            '--skip-safety-backup',
            action='store_true',
            help='Skip creating a pre-restoration safety snapshot (not recommended).'
        )
        parser.add_argument(
            '--actor',
            type=str,
            default='system_recovery',
            help='Email of administrator performing the restoration.'
        )

    def handle(self, *args, **options):
        confirm = options['confirm']
        actor = options['actor']
        target_file = options['file']
        use_latest = options['latest']
        backup_id = options['backup_id']
        skip_safety = options['skip_safety_backup']

        self.stdout.write(self.style.WARNING("=== TeamNext ERP Disaster Recovery & Database Restoration ==="))

        # 1. Resolve backup file
        backup_path = None
        base_dir = Path(settings.BACKUP_DIR)

        if backup_id:
            try:
                record = DatabaseBackupRecord.objects.get(id=backup_id)
                backup_path = Path(record.filepath)
                self.stdout.write(f"Selected backup by Record ID #{backup_id}: {backup_path}")
            except DatabaseBackupRecord.DoesNotExist:
                self.stderr.write(self.style.ERROR(f"Backup record ID #{backup_id} not found."))
                sys.exit(1)

        elif target_file:
            backup_path = Path(target_file)

        elif use_latest:
            all_backups = list(base_dir.rglob('*.json.gz'))
            if not all_backups:
                self.stderr.write(self.style.ERROR(f"No backup archives (.json.gz) found in {base_dir}."))
                sys.exit(1)
            backup_path = sorted(all_backups, key=lambda p: p.stat().st_mtime, reverse=True)[0]
            self.stdout.write(f"Located newest backup archive: {backup_path}")

        else:
            self.stderr.write(self.style.ERROR("Please specify --file=<path>, --latest, or --backup-id=<id> to restore."))
            sys.exit(1)

        if not backup_path.exists():
            self.stderr.write(self.style.ERROR(f"Backup file does not exist: {backup_path}"))
            sys.exit(1)

        # 2. Safety confirmation check
        if confirm != "CONFIRM_RESTORE":
            self.stderr.write(self.style.ERROR(
                "\nSAFETY SAFEGUARD: Restoring a database replaces or updates active records.\n"
                "To proceed, rerun the command with --confirm=CONFIRM_RESTORE"
            ))
            sys.exit(1)

        # 3. Verify backup file integrity before applying
        self.stdout.write(f"Verifying integrity of {backup_path.name}...")
        sha256 = hashlib.sha256()
        with open(backup_path, 'rb') as f:
            while chunk := f.read(65536):
                sha256.update(chunk)
        calc_sha256 = sha256.hexdigest()
        self.stdout.write(f"Archive SHA-256: {calc_sha256}")

        # Check decompression
        try:
            with gzip.open(backup_path, 'rt', encoding='utf-8') as gz:
                test_parse = json.load(gz)
            self.stdout.write(self.style.SUCCESS(f"[OK] Backup decompression and structure valid ({len(test_parse)} entities)."))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"FATAL: Backup file is corrupted or unreadable: {e}"))
            sys.exit(1)

        # 4. Create Pre-Restoration Safety Snapshot
        if not skip_safety:
            self.stdout.write("Generating pre-restoration safety snapshot of current active state...")
            try:
                call_command('db_backup', type='pre_deployment', actor=actor)
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Pre-restore safety snapshot warning: {e}"))

        # 5. Execute Restoration
        self.stdout.write("Restoring database records from archive...")
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as tmp_file:
            temp_json = Path(tmp_file.name)

        try:
            with gzip.open(backup_path, 'rb') as f_in:
                with open(temp_json, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)

            # Apply records safely using Django loaddata
            call_command('loaddata', str(temp_json))
            self.stdout.write(self.style.SUCCESS("[OK] Data successfully loaded into database."))

        except Exception as e:
            self.stderr.write(self.style.ERROR(f"FATAL: Restoration failed during loaddata: {e}"))
            sys.exit(1)
        finally:
            if temp_json.exists():
                temp_json.unlink()

        # 6. Post-restore Verification & Entity Counts
        try:
            co_count = Company.all_objects.count()
            emp_count = Employee.all_objects.count()
            self.stdout.write(self.style.SUCCESS(
                f"[OK] Post-restore verification complete: {co_count} Companies, {emp_count} Employees active/preserved."
            ))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Could not read entity counts: {e}"))

        # 7. Audit Log
        log_audit(
            actor_email=actor,
            action='RECOVERY',
            entity_type='DatabaseRestoration',
            entity_id=backup_path.name,
            entity_name="Database Restored",
            description=f"Database restored from backup archive {backup_path.name} (SHA-256: {calc_sha256[:16]}...)"
        )

        self.stdout.write(self.style.SUCCESS(f"=== Database Restoration Succeeded: {backup_path.name} ==="))
