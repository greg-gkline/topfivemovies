#!/bin/bash
# Runs on every container start, then hands off to the stock PHP/Apache entrypoint.
#  1. waits for MySQL
#  2. creates the databases and loads data/*.sql if they are empty
#  3. generates fresh random passwords for the read-only users and applies them
#  4. writes them to /etc/topfive/db.php, which web/includes/common.php3 includes
set -euo pipefail

DATA_DIR=/workspaces/topfivemovies/data
CONFIG_DIR=/etc/topfive
CONFIG_FILE=$CONFIG_DIR/db.php

# user name in common.php3 -> database -> dump file
PRIMARY_DB=gklinec_top5primary; PRIMARY_USER=gklinec_top5prim; PRIMARY_DUMP=$DATA_DIR/gklinec_top5primary.sql
POLL_DB=gklinec_poll;           POLL_USER=gklinec_poll;        POLL_DUMP=$DATA_DIR/gklinec_poll.sql

root_mysql() { mysql -h "$DB_HOST" -uroot -p"$DB_ROOT_PASSWORD" "$@"; }
random_password() { head -c 24 /dev/urandom | od -An -tx1 | tr -d ' \n'; }

echo "topfive: waiting for MySQL at $DB_HOST..."
until root_mysql -e 'SELECT 1' >/dev/null 2>&1; do sleep 1; done

load_db() { # db dump
	root_mysql -e "CREATE DATABASE IF NOT EXISTS \`$1\`"
	local tables
	tables=$(root_mysql -N -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='$1'")
	if [ "$tables" = "0" ]; then
		echo "topfive: loading $2 into $1"
		root_mysql "$1" < "$2"
	fi
}

# SELECT plus temp tables only: classes.php builds temporary tables for search.
# Writes (poll votes, responses) will fail until a writable user is added.
grant_readonly() { # db user password
	root_mysql -e "GRANT SELECT, CREATE TEMPORARY TABLES ON \`$1\`.* TO '$2'@'%' IDENTIFIED BY '$3'"
}

load_db "$PRIMARY_DB" "$PRIMARY_DUMP"
load_db "$POLL_DB" "$POLL_DUMP"

PRIMARY_PASSWORD=$(random_password)
POLL_PASSWORD=$(random_password)
grant_readonly "$PRIMARY_DB" "$PRIMARY_USER" "$PRIMARY_PASSWORD"
grant_readonly "$POLL_DB" "$POLL_USER" "$POLL_PASSWORD"
root_mysql -e 'FLUSH PRIVILEGES'

mkdir -p "$CONFIG_DIR"
umask 027
cat > "$CONFIG_FILE" <<PHP
<?php
// Generated at container startup by topfive-entrypoint. Do not edit or commit.
\$hostname = "$DB_HOST";
\$primary_password = "$PRIMARY_PASSWORD";
\$poll_password = "$POLL_PASSWORD";
?>
PHP
chown root:www-data "$CONFIG_FILE"
chmod 640 "$CONFIG_FILE"
echo "topfive: read-only DB passwords written to $CONFIG_FILE"

exec docker-php-entrypoint "$@"
