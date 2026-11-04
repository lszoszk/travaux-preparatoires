#!/bin/bash
# On the VM, daily (cron 03:40): a dated copy of the publication audit's answers (the annotators write them into
# /mnt/data2/travaux/audit/round, outside the bundle), kept 90 days. deploy/backup_to_vm.sh brings the copies to the laptop.
set -euo pipefail
SRC=/mnt/data2/travaux/audit/round
DEST=/mnt/data2/travaux/backup/audit
mkdir -p "$DEST"
tar -czf "$DEST/round-$(date +%F).tgz" -C "$(dirname "$SRC")" "$(basename "$SRC")"
find "$DEST" -name 'round-*.tgz' -mtime +90 -delete
