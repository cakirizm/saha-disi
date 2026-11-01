#!/usr/bin/env bash
# Hourly on the project server: read partner channels' videos and push only
# backend/youtube_candidates.json. GitHub Actions builds the feed from it, so this
# job never touches feed.json and the two never fight over the same file.
set -euo pipefail

REPO=${REPO:-/opt/saha-disi}
PY=${PY:-/opt/sahadisi-venv/bin/python}
cd "$REPO"

# API keys (TranscriptYT, YouTube Data API) stay on the server, outside the repo.
if [ -f /etc/sahadisi.env ]; then set -a; . /etc/sahadisi.env; set +a; fi

git pull -q --rebase origin main
"$PY" backend/youtube_partner.py

git add backend/youtube_candidates.json
if git diff --cached --quiet; then
  echo "yeni video sözü yok"
  exit 0
fi
git -c user.name="saha-disi-youtube" -c user.email="saha-disi-youtube@users.noreply.github.com" \
  commit -q -m "data: partner YouTube statements [skip ci]"

for attempt in 1 2 3; do
  if git push -q origin main; then
    echo "gönderildi"
    exit 0
  fi
  git pull -q --rebase -X theirs origin main
done
echo "push başarısız" >&2
exit 1
