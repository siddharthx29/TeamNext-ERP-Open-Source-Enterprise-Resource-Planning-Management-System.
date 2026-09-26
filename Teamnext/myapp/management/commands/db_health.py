import time
import json
import sys
from pathlib import Path
from datetime import datetime, timedelta

from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import connection
from django.utils import timezone

from myapp.models import (
    Company, Employee, Invoice, Ticket, ProjectTask, DatabaseBackupRecord
)


class Command(BaseCommand):
    help = "Performs a complete database persistence, connectivity, and backup recency health audit."

    def add_arguments(self, parser):
        parser.add_argument(
            '--format',
            type=str,
            choices=['text', 'json'],
            default='text',
            help='Output format: text or json.'
        )
        parser.add_argument(
            '--strict',
            action='store_true',
            help='Exit with non-zero status code if any critical alerts or corruption risks are detected.'
        )

    def handle(self, *args, **options):
        output_format = options['format']
        health_report = {
            'timestamp': timezone.now().isoformat(),
            'healthy': True,
            'database': {},
            'persistence': {},
            'backups': {},
            'entities': {},
            'alerts': []
        }

        # 1. Test database connection & latency
        db_conf = settings.DATABASES['default']
        db_engine = db_conf.get('ENGINE', '')
        engine_short = 'postgresql' if 'postgres' in db_engine else ('mysql' if 'mysql' in db_engine else 'sqlite3')

        t_start = time.time()
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1;")
                row = cursor.fetchone()
            latency_ms = round((time.time() - t_start) * 1000, 2)
            conn_ok = bool(row and row[0] == 1)
        except Exception as e:
            conn_ok = False
            latency_ms = -1
            health_report['alerts'].append(f"CRITICAL: Database connection failed: {e}")
            health_report['healthy'] = False

        health_report['database'] = {
            'engine': engine_short,
            'full_engine': db_engine,
            'name': str(db_conf.get('NAME', '')),
            'host': db_conf.get('HOST', 'localhost' if engine_short != 'sqlite3' else 'local_disk'),
            'connected': conn_ok,
            'latency_ms': latency_ms,
        }

        # 2. Persistence check
        is_production = getattr(settings, 'DJANGO_ENV', 'development') == 'production' or not settings.DEBUG
        allow_sqlite = getattr(settings, 'ALLOW_SQLITE_IN_PRODUCTION', False)

        persistence_safe = True
        if is_production and engine_short == 'sqlite3' and not allow_sqlite:
            persistence_safe = False
            msg = "CRITICAL: Ephemeral SQLite database detected in production! Server restart/redeploy will destroy data."
            health_report['alerts'].append(msg)
            health_report['healthy'] = False

        health_report['persistence'] = {
            'environment': getattr(settings, 'DJANGO_ENV', 'development'),
            'is_production': is_production,
            'persistence_safe': persistence_safe,
            'storage_type': 'external_persistent_service' if engine_short != 'sqlite3' else 'local_filesystem'
        }

        # 3. Backup Recency Check
        latest_verified = DatabaseBackupRecord.objects.filter(status='verified').order_by('-created_at').first()
        backup_fresh = False
        last_backup_age_hours = None

        if latest_verified:
            age_delta = timezone.now() - latest_verified.created_at
            last_backup_age_hours = round(age_delta.total_seconds() / 3600, 1)
            backup_fresh = last_backup_age_hours <= 24.0

            if not backup_fresh:
                health_report['alerts'].append(
                    f"WARNING: Latest backup is {last_backup_age_hours} hours old (> 24h threshold)."
                )
        else:
            # Check manifest on disk
            manifest_path = Path(settings.BACKUP_DIR) / 'manifest.json'
            if not manifest_path.exists():
                health_report['alerts'].append("WARNING: No verified backup record or manifest found. Run db_backup immediately.")

        health_report['backups'] = {
            'latest_backup_file': latest_verified.filename if latest_verified else None,
            'latest_backup_time': latest_verified.created_at.isoformat() if latest_verified else None,
            'age_hours': last_backup_age_hours,
            'is_fresh_under_24h': backup_fresh,
            'total_recorded_backups': DatabaseBackupRecord.objects.count()
        }

        # 4. Entity summary & Soft Delete audit
        try:
            active_cos = Company.objects.count()
            soft_del_cos = Company.all_objects.filter(is_deleted=True).count()
            active_emps = Employee.objects.count()
            soft_del_emps = Employee.all_objects.filter(is_deleted=True).count()
            active_invs = Invoice.objects.count()
            soft_del_invs = Invoice.all_objects.filter(is_deleted=True).count()
            active_tasks = ProjectTask.objects.count()
            soft_del_tasks = ProjectTask.all_objects.filter(is_deleted=True).count()

            health_report['entities'] = {
                'companies': {'active': active_cos, 'soft_deleted': soft_del_cos},
                'employees': {'active': active_emps, 'soft_deleted': soft_del_emps},
                'invoices': {'active': active_invs, 'soft_deleted': soft_del_invs},
                'tasks': {'active': active_tasks, 'soft_deleted': soft_del_tasks},
            }
        except Exception as e:
            health_report['alerts'].append(f"Entity count read error: {e}")

        # Output formatting
        if output_format == 'json':
            self.stdout.write(json.dumps(health_report, indent=2))
        else:
            self.stdout.write("=" * 70)
            self.stdout.write(f"TEAMNEXT ERP DATABASE HEALTH AUDIT: {health_report['timestamp']}")
            self.stdout.write("=" * 70)

            status_style = self.style.SUCCESS("HEALTHY") if health_report['healthy'] else self.style.ERROR("ATTENTION REQUIRED")
            self.stdout.write(f"Overall Status: {status_style}")
            self.stdout.write(f"Database Engine: {health_report['database']['engine']} ({health_report['database']['host']})")
            self.stdout.write(f"Connection Probe: {'[OK] Active' if conn_ok else '[FAIL] Failed'} ({latency_ms} ms)")
            self.stdout.write(f"Persistence Tier: {health_report['persistence']['storage_type']}")

            if health_report['backups']['latest_backup_file']:
                self.stdout.write(
                    f"Latest Backup: {health_report['backups']['latest_backup_file']} "
                    f"({health_report['backups']['age_hours']}h ago, Fresh: {'[OK]' if backup_fresh else '[WARN]'})"
                )
            else:
                self.stdout.write(self.style.WARNING("Latest Backup: None detected"))

            self.stdout.write("\nActive vs Soft-Deleted Entity Ledger:")
            for ent, counts in health_report['entities'].items():
                self.stdout.write(f"  - {ent.capitalize():<12}: {counts['active']} active | {counts['soft_deleted']} soft-deleted (recoverable)")

            if health_report['alerts']:
                self.stdout.write("\nActive Alerts:")
                for alert in health_report['alerts']:
                    self.stdout.write(self.style.ERROR(f"  ! {alert}"))
            self.stdout.write("=" * 70)

        if not health_report['healthy'] and options.get('strict', False):
            sys.exit(1)
