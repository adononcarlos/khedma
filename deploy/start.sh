#!/bin/bash
# Démarrage du Space : base restaurée depuis l'export, puis API (8010, interne) et interface (7860, publique)
set -e
export PGDATA="$HOME/pgdata"
if [ ! -s "$PGDATA/PG_VERSION" ]; then
  initdb -D "$PGDATA" -U khedma --auth=trust -E UTF8 >/dev/null
  pg_ctl -D "$PGDATA" -o "-c listen_addresses=127.0.0.1 -p 5432 -c unix_socket_directories=$HOME" -l "$HOME/pg.log" -w start
  createdb -h 127.0.0.1 -U khedma khedma
  pg_restore -h 127.0.0.1 -U khedma -d khedma --no-owner --no-privileges /app/deploy/khedma.dump || true
else
  pg_ctl -D "$PGDATA" -o "-c listen_addresses=127.0.0.1 -p 5432 -c unix_socket_directories=$HOME" -l "$HOME/pg.log" -w start
fi
cd /app/backend
uvicorn app.main:app --host 127.0.0.1 --port 8010 &
until curl -sf http://127.0.0.1:8010/api/health >/dev/null; do sleep 1; done
cd /app/frontend
exec env PORT=7860 HOSTNAME=0.0.0.0 node server.js
