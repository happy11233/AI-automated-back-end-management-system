#!/usr/bin/env bash
set -euo pipefail
umask 077
# libpq reads PGSERVICE/PGPASSFILE/PG*; credentials do not enter argv.
if [[ $# -ne 1 ]]; then
  echo 'Usage: scripts/backup_database.sh /secure/backup-directory' >&2
  exit 2
fi
mkdir -p "$1"
destination="$1/company-rag-$(date -u +%Y%m%dT%H%M%SZ).dump"
temporary="$destination.partial"
trap 'rm -f "$temporary"' EXIT
pg_dump --format=custom --no-owner --no-acl --file="$temporary"
pg_restore --list "$temporary" >/dev/null
mv "$temporary" "$destination"
echo "Backup verified: $destination"
