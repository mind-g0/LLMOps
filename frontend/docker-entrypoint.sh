#!/bin/sh
# Inject runtime env into index.html before nginx starts.
# No .env needed at build time. Pass VITE_API_BASE_URL at docker run.
set -e

HTML=/usr/share/nginx/html/index.html

HEAD_LINE=$(grep -n '</head>' "$HTML" | head -1 | cut -d: -f1)
if [ -z "$HEAD_LINE" ]; then
  echo "ERROR: </head> not found in index.html" >&2
  exit 1
fi

{
  head -n $((HEAD_LINE - 1)) "$HTML"
  printf '<script>window.__RUNTIME_CONFIG__={VITE_API_BASE_URL:"%s"};</script>\n' "${VITE_API_BASE_URL:-http://localhost:8004}"
  echo '</head>'
  tail -n +$((HEAD_LINE + 1)) "$HTML"
} > /tmp/index.html

mv /tmp/index.html "$HTML"

exec "$@"