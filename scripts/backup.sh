#!/bin/bash
set -e

# Configuration
BACKUP_DIR="/backups"
DB_HOST="${DB_HOST:-db}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-trace}"
DB_USER="${DB_USER:-trace}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/trace_${TIMESTAMP}.sql.gz"

# Ensure backup directory exists
mkdir -p "$BACKUP_DIR"

echo "[$(date)] Starting backup of ${DB_NAME}..."

# Run pg_dump and compress
PGPASSWORD="${POSTGRES_PASSWORD}" pg_dump \
  -h "$DB_HOST" \
  -p "$DB_PORT" \
  -U "$DB_USER" \
  -d "$DB_NAME" \
  --no-owner \
  --no-privileges \
  -F p \
  | gzip > "$BACKUP_FILE"

BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
echo "[$(date)] Backup completed: ${BACKUP_FILE} (${BACKUP_SIZE})"

# Rotate old backups (keep last N days)
echo "[$(date)] Rotating backups older than ${RETENTION_DAYS} days..."
find "$BACKUP_DIR" -name "trace_*.sql.gz" -mtime "+${RETENTION_DAYS}" -delete

REMAINING=$(find "$BACKUP_DIR" -name "trace_*.sql.gz" | wc -l)
echo "[$(date)] Rotation complete. ${REMAINING} backup(s) remaining."
