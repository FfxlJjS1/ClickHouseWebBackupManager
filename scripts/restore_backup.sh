#!/bin/bash

if [ -z "$1" ]; then
    echo "Backup name not specified"
    exit 1
fi

echo "Restoring backup: $1"
clickhouse-backup restore $1
exit $?