import os
import json
import sqlite3
from datetime import datetime, time
from typing import Any, Dict, List, Optional
from clickhouse_driver import Client, errors as clickhouse_errors
from environments import BACKUP_META_DB
from logger import logger
import threading
from queue import Queue

class SQLiteConnectionPool:
    """Пул соединений для SQLite с thread-safe управлением"""
    def __init__(self, db_path: str, pool_size: int = 5):
        self.db_path = db_path
        self.pool_size = pool_size
        self._lock = threading.Lock()
        self._connections = Queue()
        self._initialize_pool()

    def _initialize_pool(self):
        with self._lock:
            for _ in range(self.pool_size):
                conn = sqlite3.connect(
                    self.db_path,
                    timeout=10,
                    check_same_thread=False
                )
                conn.row_factory = sqlite3.Row
                self._connections.put(conn)

    def get_connection(self):
        return self._connections.get()

    def return_connection(self, conn):
        self._connections.put(conn)

    def close_all(self):
        while not self._connections.empty():
            conn = self._connections.get()
            conn.close()

class BackupManager:
    def __init__(self, db_path: str = BACKUP_META_DB):
        self.db_path = db_path
        self.pool = SQLiteConnectionPool(db_path)
        self._init_db()
        
    def _init_db(self):
        conn = self.pool.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS backups (
                    id TEXT PRIMARY KEY,
                    database TEXT NOT NULL,
                    type TEXT NOT NULL,
                    destination TEXT NOT NULL,
                    base_backup TEXT,
                    timestamp DATETIME NOT NULL,
                    status TEXT NOT NULL,
                    size INTEGER,
                    description TEXT
                )
            ''')
            conn.commit()
        finally:
            self.pool.return_connection(conn)

    def add_backup(self, backup_info: Dict[str, Any]) -> None:
        conn = self.pool.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO backups (
                    id, database, type, destination, 
                    base_backup, timestamp, status, size, description
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                backup_info['id'],
                backup_info['database'],
                backup_info['type'],
                backup_info['destination'],
                backup_info.get('base_backup'),
                backup_info['timestamp'],
                backup_info['status'],
                backup_info.get('size'),
                backup_info.get('description')
            ))
            conn.commit()
        finally:
            self.pool.return_connection(conn)

    def update_backup(self, backup_id: str, updates: Dict[str, Any]) -> None:
        """Обновляет метаданные существующего бэкапа"""
        conn = self.pool.get_connection()
        try:
            cursor = conn.cursor()
            set_clause = ", ".join([f"{key} = ?" for key in updates.keys()])
            values = list(updates.values())
            values.append(backup_id)
            cursor.execute(f"""
                UPDATE backups 
                SET {set_clause}
                WHERE id = ?
            """, values)
            conn.commit()
        finally:
            self.pool.return_connection(conn)

    def remove_backup(self, backup_id: str) -> Optional[Dict[str, Any]]:
        conn = self.pool.get_connection()
        try:
            cursor = conn.cursor()
            
            # Проверка существования бэкапа
            cursor.execute("SELECT * FROM backups WHERE id = ?", (backup_id,))
            backup = cursor.fetchone()
            if not backup:
                logger.debug(f"Backup {backup_id} not found")
                return None
                
            # Проверка зависимостей
            cursor.execute("SELECT id FROM backups WHERE base_backup = ?", (backup_id,))
            if cursor.fetchone():
                logger.debug(f"Cannot delete backup {backup_id}: dependent backups exist")
                return None
                
            # Удаление бэкапа
            cursor.execute("DELETE FROM backups WHERE id = ?", (backup_id,))
            conn.commit()
            logger.debug(f"Backup {backup_id} metadata removed")
            
            return dict(backup)
        finally:
            self.pool.return_connection(conn)

    def get_backup(self, backup_id: str) -> Optional[Dict[str, Any]]:
        conn = self.pool.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM backups WHERE id = ?", (backup_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            self.pool.return_connection(conn)

    def list_backups(self, database: Optional[str] = None) -> List[Dict[str, Any]]:
        conn = self.pool.get_connection()
        try:
            cursor = conn.cursor()
            if database:
                cursor.execute("SELECT * FROM backups WHERE database = ?", (database,))
            else:
                cursor.execute("SELECT * FROM backups")
            return [dict(row) for row in cursor.fetchall()]
        finally:
            self.pool.return_connection(conn)

class ClickHouseBackup:
    def __init__(self, host="localhost", port=9000, user="default", password="", database="default"):
        self.client = Client(host=host, port=port, user=user, password=password, database=database)
        self.meta = BackupManager()

    def _get_backup_size(self, backup_destination: str) -> int:
        """Вычисляет размер бэкапа в байтах"""
        try:
            # Извлекаем путь из формата "File('/path/to/backup')"
            if backup_destination.startswith("File('") and backup_destination.endswith("')"):
                path = backup_destination[6:-2]
                if os.path.exists(path):
                    total_size = 0
                    for dirpath, _, filenames in os.walk(path):
                        for f in filenames:
                            fp = os.path.join(dirpath, f)
                            if os.path.isfile(fp):
                                total_size += os.path.getsize(fp)
                    return total_size
            return 0
        except Exception as e:
            logger.error(f"Ошибка вычисления размера бэкапа: {str(e)}")
            return 0
        
    def _complete_backup_metadata(self, op_id: str, destination: str, backup_id: str):
        """
        Фоновая задача для завершения метаданных бэкапа
        """
        try:
            final_status = self.wait_for_operation(op_id)
            size = self._get_backup_size(destination)
            self.meta.update_backup(backup_id, {
                "status": final_status,
                "size": size
            })
        except RuntimeError as e:
            logger.error(f"Ошибка при выполнении бэкапа {op_id}: {str(e)}")
            self.meta.update_backup(backup_id, {"status": "BACKUP_FAILED"})
        except Exception as e:
            logger.error(f"Неизвестная ошибка при выполнении бэкапа {op_id}: {str(e)}")
            self.meta.update_backup(backup_id, {"status": "BACKUP_FAILED"})

    def wait_for_operation(self, op_id: str, poll_sec: int = 2) -> str:
        """Ожидает завершения операции и возвращает финальный статус"""
        while True:
            rows = self.client.execute("SELECT status, error FROM system.backups WHERE id = %(id)s", {"id": op_id})
            if not rows:
                logger.debug(f"Операция {op_id} не найдена в system.backups")
                return "NOT_FOUND"
            status, error = rows[0]
            if status in ("BACKUP_CREATED", "RESTORED"):
                logger.debug(f"Операция {op_id} завершена со статусом {status}")
                return status
            if status in ("BACKUP_FAILED", "RESTORE_FAILED"):
                raise RuntimeError(f"Операция {op_id} провалена: {error}")
            logger.debug(f"Статус {status}...")
            time.sleep(poll_sec)

    def backup_full(self, database: str, destination: str, async_mode: bool = False, description: Optional[str] = None) -> None:
        query = f"BACKUP DATABASE {database} TO {destination}"
        if async_mode:
            query += " ASYNC"
        logger.debug(f"Выполняется: {query}")
        op_id, initial_status = self.client.execute(query)[0]
        logger.debug(f"ID операции: {op_id}, статус: {initial_status}")

        # Добавляем запись сразу после запуска операции
        self.meta.add_backup({
            "id": op_id,
            "database": database,
            "type": "full",
            "destination": destination,
            "base_backup": None,
            "timestamp": datetime.now().isoformat(),
            "status": initial_status,
            "size": 0,  # Временно 0
            "description": description
        })

        if async_mode:
            # Запускаем фоновый поток для отслеживания завершения
            threading.Thread(
                target=self._complete_backup_metadata,
                args=(op_id, destination, op_id),
                daemon=True
            ).start()
        else:
            # Синхронный режим: ждем завершения здесь
            try:
                final_status = self.wait_for_operation(op_id)
                size = self._get_backup_size(destination)
                self.meta.update_backup(op_id, {
                    "status": final_status,
                    "size": size
                })
            except Exception as e:
                self.meta.update_backup(op_id, {"status": "BACKUP_FAILED"})
                logger.error(f"Ошибка при создании бэкапа: {str(e)}")
                raise

    def backup_incremental(self, database: str, destination: str, base_backup_id: str, async_mode: bool = False, description: Optional[str] = None) -> None:
        base_backup = self.meta.get_backup(base_backup_id)
        if not base_backup:
            raise ValueError(f"Базовый бэкап {base_backup_id} не найден в метаданных")
        base_expr = base_backup["destination"]
        query = f"BACKUP DATABASE {database} TO {destination} SETTINGS base_backup = {base_expr}"
        if async_mode:
            query += " ASYNC"
        logger.debug(f"Выполняется: {query}")
        op_id, initial_status = self.client.execute(query)[0]
        logger.debug(f"ID операции: {op_id}, статус: {initial_status}")

        # Добавляем запись сразу после запуска операции
        self.meta.add_backup({
            "id": op_id,
            "database": database,
            "type": "incremental",
            "destination": destination,
            "base_backup": base_backup_id,
            "timestamp": datetime.now().isoformat(),
            "status": initial_status,
            "size": 0,  # Временно 0
            "description": description
        })

        if async_mode:
            # Запускаем фоновый поток для отслеживания завершения
            threading.Thread(
                target=self._complete_backup_metadata,
                args=(op_id, destination, op_id),
                daemon=True
            ).start()
        else:
            # Синхронный режим: ждем завершения здесь
            try:
                final_status = self.wait_for_operation(op_id)
                size = self._get_backup_size(destination)
                self.meta.update_backup(op_id, {
                    "status": final_status,
                    "size": size
                })
            except Exception as e:
                self.meta.update_backup(op_id, {"status": "BACKUP_FAILED"})
                logger.error(f"Ошибка при создании инкрементального бэкапа: {str(e)}")
                raise

    def restore(self, database: str, source: str,
                async_mode: bool = False) -> None:
        # Удаление всех таблиц в базе (если база существует)
        try:
            tables = self.get_tables(database)
            for table in tables:
                logger.debug(f"Удаление таблицы: {database}.{table}")
                # Для асинхронного режима используем SYNC для гарантии удаления
                self.client.execute(f"DROP TABLE IF EXISTS {database}.{table} SYNC")
        except clickhouse_errors.ServerException as e:
            if "Database doesn't exist" not in str(e):
                logger.error(f"Ошибка при очистке базы: {str(e)}")
                raise
        
        # Выполнение восстановления
        query = f"RESTORE DATABASE {database} FROM {source}"
        if async_mode:
            query += " ASYNC"

        logger.debug(f"Выполняется: {query}")
        try:
            op_id, status = self.client.execute(query)[0]
            logger.debug(f"ID операции: {op_id}, статус: {status}")
            
            if not async_mode:
                self.wait_for_operation(op_id)
        except Exception as e:
            logger.error(f"Ошибка при восстановлении: {str(e)}")
            raise
        
    def list_databases(self) -> List[str]:
        rows = self.client.execute("SHOW DATABASES")
        return [row[0] for row in rows]
    
    def get_tables(self, database: str) -> List[str]:
        """Получить список таблиц в указанной базе данных"""
        try:
            tables = self.client.execute(
                "SELECT name FROM system.tables WHERE database = %(database)s",
                {"database": database}
            )
            return [table[0] for table in tables]
        except clickhouse_errors.ServerException as e:
            # Если база не существует, вернем пустой список
            if "Database" in e.message and "doesn't exist" in e.message:
                return []
            raise
