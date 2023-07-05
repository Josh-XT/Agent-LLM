#!/bin/sh

set -e

host="${POSTGRES_SERVER:-db}"
port="${POSTGRES_PORT:-5432}"
db="${POSTGRES_DB:-postgres}"
sleep 30

until PGPASSWORD=$POSTGRES_PASSWORD psql -h "$host" -p "$port" -U "$POSTGRES_USER" -c '\q'; do
  >&2 echo "Waiting for database... $host:$port"
  sleep 1
done

# Check if the database exists, and create it if it doesn't
PGPASSWORD=$POSTGRES_PASSWORD psql -h "$host" -p "$port" -U "$POSTGRES_USER" -tc "SELECT 1 FROM pg_database WHERE datname = '$db'" | grep -q 1 || PGPASSWORD=$POSTGRES_PASSWORD createdb -h "$host" -p "$port" -U "$POSTGRES_USER" "$db"
sleep 5

python3 DBConnection.py
python3 Hub.py

echo "Starting AGiXT..."
# Start the Uvicorn server
uvicorn app:app --host 0.0.0.0 --port 7437 --workers "$UVICORN_WORKERS" --proxy-headers
