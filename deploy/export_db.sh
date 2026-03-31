#!/bin/bash
# Exporte la base pour le déploiement : offres + comptes de démonstration uniquement (aucun compte réel).
set -e
cd "$(dirname "$0")"
docker exec khedma-db psql -U khedma -qc "DROP DATABASE IF EXISTS khedma_export" -d postgres
docker exec khedma-db psql -U khedma -qc "CREATE DATABASE khedma_export" -d postgres
# Copie par sauvegarde/restauration (fonctionne même si l'API est connectée à la base)
docker exec khedma-db sh -c "pg_dump -U khedma -d khedma -Fc | pg_restore -U khedma -d khedma_export --no-owner"
docker exec khedma-db psql -U khedma -d khedma_export -q -c "
  CREATE TEMP TABLE out_users AS SELECT id FROM users WHERE NOT is_demo AND email <> 'yassine.demo@example.com';
  DELETE FROM applications WHERE user_id IN (SELECT id FROM out_users);
  DELETE FROM generated_documents WHERE user_id IN (SELECT id FROM out_users);
  DELETE FROM profiles WHERE user_id IN (SELECT id FROM out_users);
  DELETE FROM users WHERE id IN (SELECT id FROM out_users);"
docker exec khedma-db pg_dump -U khedma -d khedma_export -Fc --no-owner --no-privileges > khedma.dump
docker exec khedma-db psql -U khedma -qc "DROP DATABASE khedma_export" -d postgres
ls -lh khedma.dump
