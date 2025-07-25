import os


CLICKHOUSE_HOST = os.getenv('CLICKHOUSE_HOST', 'clickhouse')
CLICKHOUSE_PORT = int(os.getenv('CLICKHOUSE_PORT', 9000))
CLICKHOUSE_USER = os.getenv('CLICKHOUSE_USER', 'admin')
CLICKHOUSE_PASSWORD = os.getenv('CLICKHOUSE_PASSWORD', 'password')
CLICKHOUSE_DB = os.getenv('CLICKHOUSE_DB', 'mydb')
BACKUP_DIR = os.getenv("BACKUP_STORAGE", "/backups")

BACKUP_META_DB = os.path.join(BACKUP_DIR, "backups.db")
