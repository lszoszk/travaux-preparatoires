#!/bin/bash
# A copy on the VM of what exists only on this laptop: the repository (a git bundle of every branch), the files git does
# not track (work in progress), data/ without the page images (ocr/*/img, which are rendered again from data/raw) and the
# vectors' parts, and eval/private (the private reference texts, never published). About 4 GB; rsync sends only what
# changed. It also brings back the VM's copies of the publication audit's answers (deploy/backup_vm_audit.sh) into
# data/private/vm_audit/. Run it after a day's work:   bash deploy/backup_to_vm.sh
set -euo pipefail
cd "$(dirname "$0")/.."
H=${TRAVAUX_VM:-amuvmuser@150.254.115.204}
DEST=/mnt/data2/travaux/backup/laptop
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
git bundle create "$TMP/travaux.bundle" --all 2>/dev/null
git ls-files --others --exclude-standard -z | tar -czf "$TMP/untracked.tgz" --null -T -
ssh "$H" "mkdir -p $DEST/data $DEST/eval-private"
rsync -a "$TMP/travaux.bundle" "$TMP/untracked.tgz" "$H:$DEST/"
rsync -a --delete --exclude 'ocr/*/img/' --exclude 'cache/vectors/*/part-*' data/ "$H:$DEST/data/"
rsync -a --delete eval/private/ "$H:$DEST/eval-private/"
mkdir -p data/private/vm_audit
rsync -a "$H:/mnt/data2/travaux/backup/audit/" data/private/vm_audit/ 2>/dev/null || true
echo "backup on $H:$DEST: $(ssh "$H" "du -sh $DEST | cut -f1"); audit copies here: $(ls data/private/vm_audit | wc -l | tr -d ' ')"
