#!/bin/sh
set -e

echo "Waiting for database at ${DATABASE_URL:-<unset>}..."
python -c "
import time, sys
from sqlalchemy import create_engine, text
from app.core.config import get_settings

for attempt in range(30):
    try:
        engine = create_engine(get_settings().DATABASE_URL)
        with engine.connect() as conn:
            conn.execute(text('SELECT 1'))
        print('Database is ready.')
        sys.exit(0)
    except Exception as e:
        print(f'  attempt {attempt+1}/30: not ready yet ({e.__class__.__name__})')
        time.sleep(2)
print('Database never became ready.', file=sys.stderr)
sys.exit(1)
"

echo "Running Alembic migrations..."
alembic upgrade head

echo "Starting application: $@"
exec "$@"
