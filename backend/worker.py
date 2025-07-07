import os
import sys
import zipfile
import json
from datetime import datetime
from clickhouse_driver import Client

host = os.getenv('CLICKHOUSE_HOST', 'clickhouse')
port = int(os.getenv('CLICKHOUSE_PORT', 9000))
user = os.getenv('CLICKHOUSE_USER', 'admin')
password = os.getenv('CLICKHOUSE_PASSWORD', 'password')
database = os.getenv('CLICKHOUSE_DB', 'mydb')
BACKUP_METADATA = "backup_metadata.json"

def create_backup(path, backup_type):
    client = Client(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database
    )
    
    # Создаем таблицу для логов бэкапов, если не существует
    client.execute("""
    CREATE TABLE IF NOT EXISTS BackupLog (
        event_time DateTime DEFAULT now(),
        event String,
        table_name String,
        rows_count UInt64
    ) ENGINE = MergeTree()
    ORDER BY event_time
    """)
    
    if backup_type == 'full':
        # Полный бэкап: экспорт всех таблиц
        tables = client.execute("SHOW TABLES")
        with zipfile.ZipFile(path, 'w') as zipf:
            metadata = {"type": "full", "timestamp": str(datetime.utcnow())}
            
            for table in tables:
                table_name = table[0]
                # Пропускаем системные таблицы
                if table_name.startswith('system.') or table_name == 'BackupLog':
                    continue
                
                # Экспорт структуры
                create_sql = client.execute(f"SHOW CREATE TABLE {table_name}")[0][0]
                zipf.writestr(f"{table_name}.sql", create_sql)
                
                # Экспорт данных
                data = client.execute_iter(f"SELECT * FROM {table_name}")
                with open(f'/tmp/{table_name}.csv', 'w') as f:
                    for row in data:
                        f.write(','.join(map(str, row)) + '\n')
                zipf.write(f'/tmp/{table_name}.csv', f"{table_name}.csv")
                os.remove(f'/tmp/{table_name}.csv')
                
                # Логируем действие
                row_count = client.execute(f"SELECT count() FROM {table_name}")[0][0]
                client.execute(
                    "INSERT INTO BackupLog (event, table_name, rows_count) VALUES",
                    [('full_backup', table_name, row_count)]
                )
            
            # Сохраняем метаданные
            zipf.writestr(BACKUP_METADATA, json.dumps(metadata))

    elif backup_type == 'incremental':
        # Инкрементный бэкап: только измененные данные
        last_backup_time = client.execute(
            "SELECT max(event_time) FROM BackupLog WHERE event = 'full_backup'"
        )[0][0] or datetime.min
        
        tables = client.execute("SHOW TABLES")
        with zipfile.ZipFile(path, 'w') as zipf:
            metadata = {"type": "incremental", "timestamp": str(datetime.utcnow())}
            changes_found = False
            
            for table in tables:
                table_name = table[0]
                # Пропускаем системные таблицы
                if table_name.startswith('system.') or table_name == 'BackupLog':
                    continue
                
                # Проверяем наличие колонки с временной меткой
                has_timestamp = client.execute(
                    f"SELECT count() FROM system.columns "
                    f"WHERE table = '{table_name}' AND name = 'updated_at'"
                )[0][0] > 0
                
                if has_timestamp:
                    # Экспорт только измененных данных
                    data = client.execute_iter(
                        f"SELECT * FROM {table_name} "
                        f"WHERE updated_at > '{last_backup_time}'"
                    )
                    
                    # Если есть изменения - сохраняем
                    row_count = 0
                    with open(f'/tmp/{table_name}.csv', 'w') as f:
                        for row in data:
                            f.write(','.join(map(str, row)) + '\n')
                            row_count += 1
                    
                    if row_count > 0:
                        changes_found = True
                        zipf.write(f'/tmp/{table_name}.csv', f"{table_name}.csv")
                        os.remove(f'/tmp/{table_name}.csv')
                        
                        # Логируем действие
                        client.execute(
                            "INSERT INTO BackupLog (event, table_name, rows_count) VALUES",
                            [('incremental_backup', table_name, row_count)]
                        )
            
            if not changes_found:
                print("No changes detected for incremental backup")
                return
            
            # Сохраняем метаданные
            zipf.writestr(BACKUP_METADATA, json.dumps(metadata))

def restore_backup(path):
    client = Client(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database
    )
    
    with zipfile.ZipFile(path, 'r') as zipf:
        # Читаем метаданные
        metadata = json.loads(zipf.read(BACKUP_METADATA).decode())
        backup_type = metadata["type"]
        
        # Восстановление структуры
        for file in zipf.namelist():
            if file.endswith('.sql'):
                sql = zipf.read(file).decode()
                try:
                    client.execute(sql)
                except Exception as e:
                    print(f"Table creation skipped (likely exists): {str(e)}")
        
        # Восстановление данных
        for file in zipf.namelist():
            if file.endswith('.csv'):
                table_name = file.split('.')[0]
                
                # Для инкрементных бэкапов не очищаем таблицу
                if backup_type == 'full':
                    try:
                        client.execute(f"TRUNCATE TABLE {table_name}")
                    except:
                        pass
                
                # Загрузка данных
                with zipf.open(file) as csv_file:
                    client.execute(
                        f"INSERT INTO {table_name} FORMAT CSV",
                        csv_file.read().decode()
                    )
        
        # Логируем восстановление
        client.execute(
            "INSERT INTO BackupLog (event) VALUES",
            [('restore_completed',)]
        )

if __name__ == "__main__":
    action = sys.argv[1]
    
    if action == "create":
        create_backup(sys.argv[2], sys.argv[3])
    elif action == "restore":
        restore_backup(sys.argv[2])