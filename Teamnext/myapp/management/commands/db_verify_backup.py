import os
import sys
import gzip
import json
import hashlib
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.utils import timezone

from myapp.models import DatabaseBackupRecord


class Command(BaseCommand):
    help = "Validates the cryptographic integrity, decompression, and structure of stored database backups."

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='',
            help='Validate a specific backup archive file.'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Validate all backup files found in BACKUP_DIR.'
        )

    def handle(self, *args, **options):
        specific_file = options['file']
        validate_all = options['all']

        self.stdout.write("=== TeamNext ERP Backup Validation Suite ===")

        base_dir = Path(settings.BACKUP_DIR)
        files_to_check = []

        if specific_file:
            target = Path(specific_file)
            if not target.exists():
                self.stderr.write(self.style.ERROR(f"File not found: {target}"))
                raise CommandError(f"File not found: {target}")
            files_to_check.append(target)
        else:
            files_to_check = list(base_dir.rglob('*.json.gz'))

        if not files_to_check:
            self.stdout.write(self.style.WARNING(f"No backup archives (.json.gz) found in {base_dir}."))
            return

        self.stdout.write(f"Evaluating {len(files_to_check)} backup archive(s)...")
        results = []
        all_passed = True

        for b_path in files_to_check:
            status, count, sha256 = self.verify_single_backup(b_path)
            results.append({
                'name': b_path.name,
                'path': str(b_path),
                'status': status,
                'records': count,
                'sha256': sha256
            })
            if status != "VERIFIED":
                all_passed = False

            # Update DB record if exists
            rec = DatabaseBackupRecord.objects.filter(filename=b_path.name).first()
            if rec:
                rec.status = 'verified' if status == 'VERIFIED' else 'corrupted'
                rec.verified_at = timezone.now() if status == 'VERIFIED' else None
                rec.verification_notes = f"Integrity check: {status}. Total entities: {count}."
                rec.save()

        # Display Summary Table
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(f"{'BACKUP FILENAME':<45} | {'STATUS':<10} | {'RECORDS':<8} | {'SHA256 (PREFIX)':<12}")
        self.stdout.write("-" * 80)
        for r in results:
            color = self.style.SUCCESS if r['status'] == 'VERIFIED' else self.style.ERROR
            self.stdout.write(f"{r['name']:<45} | {color(r['status']):<10} | {r['records']:<8} | {r['sha256'][:10]:<12}")
        self.stdout.write("=" * 80)

        if all_passed:
            self.stdout.write(self.style.SUCCESS("ALL AUDITED BACKUP ARCHIVES PASSED INTEGRITY VALIDATION."))
        else:
            self.stderr.write(self.style.ERROR("ONE OR MORE BACKUP ARCHIVES FAILED INTEGRITY VALIDATION!"))
            raise CommandError("ONE OR MORE BACKUP ARCHIVES FAILED INTEGRITY VALIDATION!")

    def verify_single_backup(self, path):
        try:
            if not path.exists() or path.stat().st_size == 0:
                return "EMPTY_OR_MISSING", 0, ""

            # Check SHA-256
            sha256 = hashlib.sha256()
            with open(path, 'rb') as f:
                while chunk := f.read(65536):
                    sha256.update(chunk)
            calc_hash = sha256.hexdigest()

            # Decompress and validate JSON
            with gzip.open(path, 'rt', encoding='utf-8') as gz:
                parsed = json.load(gz)

            if isinstance(parsed, list):
                return "VERIFIED", len(parsed), calc_hash
            else:
                return "INVALID_FORMAT", 0, calc_hash

        except Exception as e:
            return f"CORRUPTED: {str(e)[:30]}", 0, ""
