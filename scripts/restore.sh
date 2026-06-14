#!/bin/bash
set -e

# Configuration
BACKUP_DIR="/backups"
DB_HOST="${DB_HOST:-db}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-trace}"
DB_USER="${DB_USER:-trace}"

# Check if backup file is provided
if [ -z "$1" ]; then
  echo "Usage: $0 <backup_file>"
  echo ""
  echo "Available backups:"
  ls -lh "$BACKUP_DIR"/trace_*.sql.gz 2>/dev/null || echo "  No backups found"
  exit 1
fi

BACKUP_FILE="$1"

# Verify file exists
if [ ! -f "$BACKUP_FILE" ]; then
  echo "Error: Backup file not found: $BACKUP_FILE"
  exit 1
fi

echo "[$(date)] WARNING: This will replace all data in '${DB_NAME}'!"
echo "[$(date)] Backup file: ${BACKUP_FILE}"
echo ""
read -p "Are you sure? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
  echo "Aborted."
  exit 0
fi

echo "[$(date)] Restoring ${DB_NAME} from ${BACKUP_FILE}..."

# Drop and recreate database
PGPASSWORD="${POSTGRES_PASSWORD}" psql \
  -h "$DB_HOST" \
  -p "$DB_PORT" \
  -U "$DB_USER" \
  -d postgres \
  -c "DROP DATABASE IF EXISTS ${DB_NAME};"

PGPASSWORD="${POSTGRES_PASSWORD}" psql \
  -h "$DB_HOST" \
  -p "$DB_PORT" \
  -U "$DB_USER" \
  -d postgres \
  -c "CREATE DATABASE ${DB_NAME} OWNER ${DB_USER};"

# Restore from backup
gunzip -c "$BACKUP_FILE" | PGPASSWORD="${POSTGRES_PASSWORD}" psql \
  -h "$DB_HOST" \
  -p "$DB_PORT" \
  -U "$DB_USER" \
  -d "$DB_NAME" \
  --quiet

echo "[$(date)] Restore completed successfully!"
echo "[$(date)] Restart the application to apply changes."
