#!/bin/bash

BACKUP_TYPE=${1:-"auto"}

if [ "$BACKUP_TYPE" == "full" ]; then
    BACKUP_NAME="full_$(date +%Y%m%d)"
    echo "Creating full backup: $BACKUP_NAME"
    clickhouse-backup create $BACKUP_NAME
    exit $?
fi

if [ "$BACKUP_TYPE" == "incremental" ]; then
    LAST_FULL=$(clickhouse-backup list | grep full_ | awk '{print $1}' | sort -r | head -n1)
    if [ -z "$LAST_FULL" ]; then
        echo "No full backup found. Creating full backup instead."
        BACKUP_NAME="full_$(date +%Y%m%d)"
        clickhouse-backup create $BACKUP_NAME
        exit $?
    fi
    BACKUP_NAME="inc_$(date +%Y%m%d)_from_${LAST_FULL}"
    echo "Creating incremental backup from $LAST_FULL: $BACKUP_NAME"
    clickhouse-backup create $BACKUP_NAME --diff-from=$LAST_FULL
    exit $?
fi

# Auto mode: full on Sunday, incremental on other days
if [ $(date +%u) -eq 7 ]; then
    BACKUP_NAME="full_$(date +%Y%m%d)"
    echo "Creating full backup: $BACKUP_NAME"
    clickhouse-backup create $BACKUP_NAME
else
    LAST_FULL=$(clickhouse-backup list | grep full_ | awk '{print $1}' | sort -r | head -n1)
    if [ -z "$LAST_FULL" ]; then
        echo "No full backup found. Creating full backup instead."
        BACKUP_NAME="full_$(date +%Y%m%d)"
        clickhouse-backup create $BACKUP_NAME
        exit $?
    fi
    BACKUP_NAME="inc_$(date +%Y%m%d)_from_${LAST_FULL}"
    echo "Creating incremental backup from $LAST_FULL: $BACKUP_NAME"
    clickhouse-backup create $BACKUP_NAME --diff-from=$LAST_FULL
fi