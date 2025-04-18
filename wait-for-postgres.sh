#!/bin/bash

set -e

host="$1"
shift
cmd="$@"

until pg_isready -h "$host" -p 5432 -U "$POSTGRES_USER"; do
  >&2 echo "PostgreSQL n'est pas encore prêt - attente..."
  sleep 1
done

>&2 echo "PostgreSQL est prêt - démarrage de application"
exec $cmd
