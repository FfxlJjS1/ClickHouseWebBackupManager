#!/bin/bash

RETENTION_DAYS=${1:-30}

# Получаем список всех бэкапов
backups=$(clickhouse-backup list | awk '{print $1}' | tail -n +2)

# Полные бэкапы
full_backups=()
for backup in $backups; do
    if [[ $backup == full_* ]]; then
        full_backups+=($backup)
    fi
done

# Удаляем старые полные бэкапы и их инкрементальные
for i in "${!full_backups[@]}"; do
    if (( i < ${#full_backups[@]} - RETENTION_DAYS )); then
        base=${full_backups[i]}
        echo "Deleting base backup: $base"
        clickhouse-backup delete $base
        
        # Удаляем связанные инкрементальные бэкапы
        for backup in $backups; do
            if [[ $backup == inc_*_from_${base} ]]; then
                echo "Deleting incremental backup: $backup"
                clickhouse-backup delete $backup
            fi
        done
    fi
done