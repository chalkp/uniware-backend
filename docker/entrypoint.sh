#!/bin/sh
set -e

echo "Waiting for database..."
python <<'PYEOF'
import os
import sys
import time

import psycopg

url = os.environ["DATABASE_URL"]
deadline = time.time() + 60
while True:
    try:
        psycopg.connect(url, connect_timeout=3).close()
        break
    except psycopg.OperationalError as exc:
        if time.time() > deadline:
            print(f"Database not reachable after 60s: {exc}", file=sys.stderr)
            sys.exit(1)
        time.sleep(1)
print("Database is up.")
PYEOF

python manage.py migrate --noinput

exec "$@"
