#!/bin/bash
# Crea database separati per app e Keycloak all'avvio del container PostgreSQL.
# Richiesto perché Keycloak non deve condividere il DB dell'applicazione.
set -e

function create_db() {
    local db=$1
    echo "Creazione database: $db"
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "postgres" <<-EOSQL
        SELECT 'CREATE DATABASE $db'
        WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$db')\gexec
EOSQL
}

if [ -n "$POSTGRES_MULTIPLE_DATABASES" ]; then
    for db in $(echo $POSTGRES_MULTIPLE_DATABASES | tr ',' ' '); do
        create_db "$db"
    done
fi
