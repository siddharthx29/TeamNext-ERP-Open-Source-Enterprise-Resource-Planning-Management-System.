# TeamNext ERP — Database Persistence, Backup & Disaster Recovery Runbook

## 1. Database Architecture Overview

TeamNext ERP is architected around durable, decoupled, multi-tier data persistence. The database lifecycle is entirely separated from the application container lifecycle.

```
                           TEAMNEXT ERP APPLICATION
                                      │
                   ┌──────────────────┴──────────────────┐
                   ▼                                     ▼
        Session / Web Requests                 Background Workers
                   │                                     │
                   └──────────────────┬──────────────────┘
                                      │ (Connection Pool / Health Checks)
                                      ▼
                      PERSISTENT ENTERPRISE DATABASE
                       (PostgreSQL Managed Cluster)
                                      │
       ┌──────────────────────────────┼──────────────────────────────┐
       ▼                              ▼                              ▼
  SOFT DELETION                 TRANSACTION AUDITING         AUTOMATED BACKUPS
- is_deleted flag              - Actor & IP tracking       - Gzip Compressed
- deleted_at / deleted_by      - Field-level changes       - Dual Format (SQL + JSON)
- Instant Admin Undo           - Immutable ledger          - SHA-256 Checksums
       │                              │                              │
       └──────────────────────────────┼──────────────────────────────┘
                                      ▼
                        LONG-TERM RETENTION & OFFSITE
                       - Daily (30 days retention)
                       - Weekly (12 weeks retention)
                       - Monthly (12 months archival)
                       - Remote Object Storage (S3 / GCS)
```

### Storage Separation Guarantee
The production database does **NOT** rely on:
- Container filesystems or local disk (`/tmp`, container `/app`)
- Application build directories
- Ephemeral Git clones
- Browser state or localStorage

---

## 2. Production Database Configuration

Production configurations must use an external, managed persistent database service (e.g. AWS RDS, Google Cloud SQL, Supabase, Neon, or Render Starter/Pro PostgreSQL).

### Supported Environment Variables

| Variable | Description | Example |
| :--- | :--- | :--- |
| `DATABASE_URL` | 12-factor database connection string (Primary) | `postgresql://teamnext:secret@db.prod.internal:5432/teamnext_prod` |
| `DB_ENGINE` | Database backend engine (Fallback) | `django.db.backends.postgresql` |
| `DB_NAME` | Database catalog name | `teamnext_prod` |
| `DB_USER` | Authenticated database user | `teamnext` |
| `DB_PASSWORD` | Database password | `StrongSecretKey2026!` |
| `DB_HOST` | Database host or cluster endpoint | `db.internal.teamnext.com` |
| `DB_PORT` | Database service port | `5432` |
| `DB_CONN_MAX_AGE` | Connection pooling persistence (seconds) | `600` |
| `DJANGO_ENV` | Operational environment profile | `production` / `staging` / `development` |
| `ALLOW_SQLITE_IN_PRODUCTION` | Safety lock: must be `True` if SQLite on persistent volume | `False` |

### Environment Isolation Rules
- **Development**: Uses local SQLite (`Teamnext/db.sqlite3`) or local container PostgreSQL.
- **Testing**: Django test runner builds an isolated test database (`test_teamnext_db`). Tests never touch production.
- **Production**: Requires persistent remote PostgreSQL service via `DATABASE_URL`. If SQLite is detected in production without `ALLOW_SQLITE_IN_PRODUCTION=True`, startup warnings and health checks alert administrators immediately.

---

## 3. Automated Backup Configuration & Storage

Backups are executed via Django management commands or triggered from the Admin Recovery Console.

### Backup Strategy & Formats
1. **Portable Relational JSON Dump (`.json.gz`)**: Full serialisation with natural primary and foreign keys. Cross-engine compatible (can be restored into SQLite, PostgreSQL, MySQL, or cloud DBs).
2. **Native Physical Snapshot**: Binary online snapshot (`sqlite3.backup` for SQLite; `pg_dump` for PostgreSQL).
3. **Cryptographic Checksumming**: Every archive generates a SHA-256 hash verified upon completion.
4. **Independent Manifest File**: Stored on disk at `backups/manifest.json` and in `DatabaseBackupRecord` database model.

### Backup Directory Hierarchy
```
backups/
├── daily/          # Automated daily snapshots (retained for 30 days)
├── weekly/         # Weekly long-term retention snapshots (retained for 12 weeks)
├── monthly/        # Monthly archival snapshots (retained for 12 months)
├── snapshots/      # Pre-deployment and pre-migration safety snapshots
└── manual/         # Manual on-demand administrative backups
```

---

## 4. Backup Retention Policy

Retention is enforced automatically on every backup execution:
- **Daily Backups**: Retained for `BACKUP_RETENTION_DAYS` (Default: `30` days). Files older than the retention window are pruned.
- **Weekly Backups**: Retained for `WEEKLY_BACKUP_RETENTION` (Default: `12` weeks).
- **Monthly Archival**: Retained for `MONTHLY_BACKUP_RETENTION` (Default: `12` months).

To customize retention via environment variables:
```bash
BACKUP_RETENTION_DAYS=60
WEEKLY_BACKUP_RETENTION=26
MONTHLY_BACKUP_RETENTION=24
```

---

## 5. How to Perform a Manual Backup

### Option A: Command Line Interface (CLI)
From the `Teamnext` directory:

```bash
# Standard manual backup with integrity verification
python manage.py db_backup --type=manual --actor="admin@teamnexterp.com"

# Pre-deployment safety snapshot
python manage.py db_backup --type=pre_deployment

# Backup with automated restoration dry-run test
python manage.py db_backup --type=manual --test-restore
```

### Option B: Administrator Web Console
1. Log in as an Administrator (`role == 'Administrator'`).
2. Navigate to **Database & Recovery** in the left sidebar (`/admin-recovery/`).
3. Click the **"Create Backup Now"** button.
4. The system triggers `db_backup`, verifies gzip and SHA-256 integrity, updates the ledger, and refreshes the table.

---

## 6. How to Verify a Backup

Never rely on unverified backup archives. TeamNext ERP includes automated integrity verification:

```bash
# Verify a specific backup file
python manage.py db_verify_backup --file=backups/daily/teamnext_backup_daily_postgresql_20260926_041434.json.gz

# Verify all backups in the catalog
python manage.py db_verify_backup --all
```

Verification verifies:
- File existence and non-zero byte size
- Cryptographic SHA-256 match
- Decompression integrity without gzip CRC/zlib errors
- Valid relational model parse and record count

---

## 7. How to Restore a Backup

### Emergency Restoration Commands

```bash
# 1. Restore from the latest verified backup archive
python manage.py db_restore --latest --confirm=CONFIRM_RESTORE

# 2. Restore from a specific backup file
python manage.py db_restore --file=backups/daily/teamnext_backup_daily_20260926_041434.json.gz --confirm=CONFIRM_RESTORE

# 3. Restore by DatabaseBackupRecord ID
python manage.py db_restore --backup-id=14 --confirm=CONFIRM_RESTORE
```

> [!IMPORTANT]
> The restore command automatically takes a **pre-restoration safety snapshot** before applying changes, ensuring that an emergency restore never causes irreversible data loss.

---

## 8. Disaster Recovery Procedures by Scenario

### Scenario A — Application / Container Restart
- **Behavior**: All persistent databases (PostgreSQL/Cloud SQL) maintain connections outside the container lifecycle.
- **Verification**: Application reconnects using connection pooling (`conn_health_checks=True`). All historical records remain intact.

### Scenario B — Server / Cloud VM Failure
- **Behavior**: Cloud database cluster fails over to standby replica.
- **Procedure**: If database host changes, update `DATABASE_URL` in environment variables and restart container.

### Scenario C — Application Redeployment
- **Behavior**: `deploy.sh` runs prior to launching the application:
  1. Creates pre-deployment safety snapshot.
  2. Applies non-destructive schema migrations.
  3. Executes `db_health` check.
  4. Launches Gunicorn.
- **Expected Result**: Existing production data remains 100% intact.

### Scenario D — Accidental Record Deletion
- **Behavior**: Important ERP entities inherit `SoftDeleteModel` (`is_deleted=True`).
- **Recovery Procedure**:
  1. Open `/admin-recovery/` in the browser.
  2. Click the **"Soft-Deleted Records"** tab.
  3. Find the deleted record (Employee, Invoice, Ticket, Task, Asset, Feedback).
  4. Click **"Restore Record"**.
  5. The entity is immediately reactivated without losing foreign-key relationships.

### Scenario E — Database Corruption
- **Recovery Procedure**:
  1. Locate newest valid backup archive using `python manage.py db_verify_backup --all`.
  2. Restore:
     ```bash
     python manage.py db_restore --latest --confirm=CONFIRM_RESTORE
     ```
  3. Validate database health:
     ```bash
     python manage.py db_health
     ```

### Scenario F — Complete Primary Database Loss (Total Wipeout)
- **Recovery Procedure**:
  1. Provision a new PostgreSQL database instance in your cloud provider.
  2. Retrieve latest backup archive from offsite storage (`s3://your-bucket/teamnext_backups/...`) or local persistent mount.
  3. Set `DATABASE_URL` pointing to the new instance.
  4. Apply baseline migrations:
     ```bash
     python manage.py migrate
     ```
  5. Restore complete ERP archive:
     ```bash
     python manage.py db_restore --file=/path/to/downloaded_backup.json.gz --confirm=CONFIRM_RESTORE --skip-safety-backup
     ```
  6. Verify all companies, employees, and business records are active:
     ```bash
     python manage.py db_health
     ```

### Scenario G — Failed Deployment or Migration Failure
- **Behavior**: `deploy.sh` takes a safety snapshot before running `migrate`.
- **Procedure**:
  1. If a migration fails, deployment halts before traffic is routed.
  2. Roll back application code to previous release.
  3. If database schema was partially modified, restore pre-deployment snapshot:
     ```bash
     python manage.py db_restore --file=backups/snapshots/teamnext_backup_pre_deployment_*.json.gz --confirm=CONFIRM_RESTORE
     ```

---

## 9. Safe Migration Strategy

Follow the non-destructive deployment sequence:

```
[1] Pre-Deployment Backup
    python manage.py db_backup --type=pre_deployment --verify
       ↓
[2] Non-Destructive Migrations
    python manage.py migrate --no-input
       ↓
[3] Health Verification
    python manage.py db_health --strict
       ↓
[4] Application Start
    gunicorn project.wsgi:application
```

### Migration Rules
- Never drop columns or tables containing active business data in a single migration step.
- Follow the two-phase deprecation pattern:
  1. Phase 1: Mark column nullable or add new column alongside old column.
  2. Phase 2: Migrate data with data migration.
  3. Phase 3: Remove old column in subsequent release after validation.

---

## 10. Audit Logging & Concurrency Protection

### Audit Logging
All critical operations (Create, Update, Soft-Delete, Restore, Backup, Recovery, and Export) are logged to `AuditLog`:
- **Actor Email & Name**: Who performed the action.
- **Action**: `CREATE`, `UPDATE`, `DELETE`, `RESTORE`, `BACKUP`, `RECOVERY`, `EXPORT`.
- **Entity**: Model name and primary key.
- **Timestamp & IP Address**: When and where the request originated.

### Concurrency Protection & Atomic Transactions
- Multi-step operations (`signup_view`, `api_create_invoice`, `api_log_expense`, `api_add_salary`, `api_hr_add_employee`) execute within `with transaction.atomic():`.
- If any sub-operation fails, the entire transaction rolls back, preventing orphaned records or corrupted state.

---

## 11. Health Probes & Monitoring

### CLI Health Probe
```bash
python manage.py db_health
```
Outputs:
- Connectivity status and roundtrip latency (ms)
- Active database engine and persistence tier
- Freshness of latest verified backup (alerts if > 24 hours old)
- Active vs soft-deleted entity count

### HTTP JSON Health Endpoint
`GET /api/health/db/`
- Returns HTTP 200 when database and backups are healthy.
- Returns HTTP 503 if database connectivity fails or critical alerts exist.
- Designed for integration with Datadog, Prometheus, Pingdom, or Render health check probes.

---

## 12. Verification & Testing

Run the full persistence test suite:
```bash
cd Teamnext
python manage.py test
```

### Tested Scenarios:
1. `test_record_persistence_across_connection_reloads`: Verifies records remain intact after query reloads.
2. `test_soft_deletion_and_restoration`: Verifies soft-deleted records are hidden from standard queries and restorable.
3. `test_soft_delete_preserves_foreign_key_relationships`: Verifies cascading deletions do not wipe linked entities.
4. `test_audit_logging_system`: Verifies audit records are properly recorded.
5. `test_atomic_transaction_rollback`: Verifies failed transactions roll back cleanly without partial writes.
6. `test_backup_command_execution_and_verification`: Verifies `db_backup` and `db_verify_backup`.
7. `test_database_health_audit_command`: Verifies `db_health`.
8. `test_admin_recovery_and_restore_api`: Verifies admin UI, restore endpoint, health API, and data export.
