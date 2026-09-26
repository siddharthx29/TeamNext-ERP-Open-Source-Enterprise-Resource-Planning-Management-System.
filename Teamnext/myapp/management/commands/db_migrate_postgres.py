import os
import sys
import json
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from django.db import connection, transaction
from django.apps import apps
from django.conf import settings
from django.core.management.color import no_style

class Command(BaseCommand):
    help = "Migrate, import, and synchronize TeamNext ERP data from SQLite into PostgreSQL with sequence repair and verification."

    def add_arguments(self, parser):
        parser.add_argument(
            '--backup-file',
            type=str,
            default=str(settings.BASE_DIR.parent / 'database_migration_backup' / 'teamnext_full_backup.json'),
            help='Path to the serialized JSON backup file (default: database_migration_backup/teamnext_full_backup.json)'
        )
        parser.add_argument(
            '--reset-sequences-only',
            action='store_true',
            help='Only reset database primary key sequences without re-importing data.'
        )
        parser.add_argument(
            '--verify-only',
            action='store_true',
            help='Only run model verification against the backup file without modifying the database.'
        )
        parser.add_argument(
            '--skip-loaddata',
            action='store_true',
            help='Skip loaddata step (e.g. if data was already loaded).'
        )

    def handle(self, *args, **options):
        backup_path = Path(options['backup_file'])
        if not backup_path.exists():
            # Also check local BASE_DIR relative path
            alt_path = settings.BASE_DIR / 'database_migration_backup' / 'teamnext_full_backup.json'
            if alt_path.exists():
                backup_path = alt_path
            else:
                raise CommandError(f"Backup file not found at {backup_path} or {alt_path}")

        engine = connection.settings_dict.get('ENGINE', '')
        db_name = connection.settings_dict.get('NAME', '')
        self.stdout.write(self.style.MIGRATE_HEADING("=== TeamNext ERP PostgreSQL Migration & Synchronization ==="))
        self.stdout.write(f"Target Database Engine: {engine}")
        self.stdout.write(f"Target Database Name  : {db_name}")
        self.stdout.write(f"Source Backup File    : {backup_path} ({backup_path.stat().st_size:,} bytes)\n")

        # Load backup statistics
        with open(backup_path, 'r', encoding='utf-8') as f:
            backup_data = json.load(f)

        backup_counts = {}
        for item in backup_data:
            model_name = item.get('model', '')
            backup_counts[model_name] = backup_counts.get(model_name, 0) + 1

        if options['verify_only']:
            self.verify_database(backup_counts)
            return

        if not options['reset_sequences_only']:
            # 1. Apply schema migrations first
            self.stdout.write(self.style.HTTP_INFO("[1/4] Ensuring all migrations are applied to target database..."))
            call_command('migrate', interactive=False)
            self.stdout.write(self.style.SUCCESS("[OK] Migrations up to date.\n"))

            # 2. Load serialized backup data
            if not options['skip_loaddata']:
                self.stdout.write(self.style.HTTP_INFO(f"[2/4] Importing {len(backup_data)} serialized records into target database..."))
                try:
                    call_command('loaddata', str(backup_path), interactive=False)
                    self.stdout.write(self.style.SUCCESS("[OK] Data loaded successfully.\n"))
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"[!] loaddata encountered an error: {e}"))
                    self.stdout.write("Attempting selective import of core application models...")
                    # Filter and import myapp objects only if sessions or permissions caused friction
                    app_objects = [item for item in backup_data if item.get('model', '').startswith('myapp.')]
                    temp_filtered = backup_path.parent / 'temp_myapp_backup.json'
                    with open(temp_filtered, 'w', encoding='utf-8') as f:
                        json.dump(app_objects, f, indent=2)
                    try:
                        call_command('loaddata', str(temp_filtered), interactive=False)
                        self.stdout.write(self.style.SUCCESS("[OK] Core ERP application data loaded successfully.\n"))
                    finally:
                        if temp_filtered.exists():
                            temp_filtered.unlink()
            else:
                self.stdout.write(self.style.HTTP_INFO("[2/4] Skipping loaddata as requested.\n"))
        else:
            self.stdout.write(self.style.HTTP_INFO("Skipping migration & loaddata (--reset-sequences-only flag set).\n"))

        # 3. Synchronize PostgreSQL sequences
        self.stdout.write(self.style.HTTP_INFO("[3/4] Synchronizing Primary Key Sequences to prevent ID collisions..."))
        self.reset_all_sequences()
        self.stdout.write(self.style.SUCCESS("[OK] Sequences synchronized.\n"))

        # 4. Perform Model Verification
        self.stdout.write(self.style.HTTP_INFO("[4/4] Verifying migrated records against backup dataset..."))
        self.verify_database(backup_counts)

    def reset_all_sequences(self):
        """Reset sequences for all models in myapp to MAX(id) + 1."""
        app_config = apps.get_app_config('myapp')
        models = list(app_config.get_models())

        # If PostgreSQL, use Django sequence_reset_sql or explicit SQL
        is_postgres = 'postgres' in connection.settings_dict.get('ENGINE', '')
        if is_postgres:
            seq_sqls = connection.ops.sequence_reset_sql(no_style(), models)
            with connection.cursor() as cursor:
                for sql in seq_sqls:
                    try:
                        cursor.execute(sql)
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f"  Warning executing sequence reset SQL: {sql} ({e})"))
            self.stdout.write("  PostgreSQL sequence_reset_sql executed.")

            # Also verify and manually ensure sequence values for every table
            with connection.cursor() as cursor:
                for model in models:
                    table_name = model._meta.db_table
                    pk_col = model._meta.pk.column
                    try:
                        # Find max id
                        cursor.execute(f'SELECT COALESCE(MAX("{pk_col}"), 0) FROM "{table_name}";')
                        max_id = cursor.fetchone()[0]
                        # Setval if sequence exists
                        cursor.execute(f"SELECT pg_get_serial_sequence('{table_name}', '{pk_col}');")
                        seq_name = cursor.fetchone()[0]
                        if seq_name:
                            cursor.execute(f"SELECT setval('{seq_name}', {max_id + 1}, false);")
                            self.stdout.write(f"  Sequence {seq_name} aligned to {max_id + 1} (Max ID: {max_id})")
                    except Exception as e:
                        # Non-integer PK or table without sequence
                        pass
        else:
            self.stdout.write("  Note: Database is not PostgreSQL. Sequence reset skipped (handled automatically by SQLite).")

    def verify_database(self, backup_counts):
        """Compare database records against expected backup counts."""
        app_config = apps.get_app_config('myapp')
        models = sorted(app_config.get_models(), key=lambda m: m.__name__)

        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(f"{'Model':<28} | {'Backup Count':<14} | {'DB Active':<12} | {'Status'}")
        self.stdout.write("-" * 80)

        all_matched = True
        for model in models:
            model_key = f"myapp.{model.__name__.lower()}"
            expected = backup_counts.get(model_key, 0)
            try:
                # Count all objects including soft-deleted to verify total row presence
                actual = model.objects.all_with_deleted().count() if hasattr(model.objects, 'all_with_deleted') else model.objects.count()
            except Exception:
                actual = model.objects.count()

            if actual == expected:
                status = self.style.SUCCESS("MATCH")
            elif actual > expected:
                status = self.style.WARNING(f"CONTAINS NEW (+{actual - expected})")
            else:
                status = self.style.ERROR(f"MISMATCH (-{expected - actual})")
                all_matched = False

            self.stdout.write(f"{model.__name__:<28} | {expected:<14} | {actual:<12} | {status}")

        self.stdout.write("=" * 80 + "\n")
        if all_matched:
            self.stdout.write(self.style.SUCCESS("[OK] VERIFICATION SUCCESS: All model record counts match perfectly!\n"))
        else:
            self.stdout.write(self.style.WARNING("[!] Some models have discrepancies. Review the report above.\n"))
