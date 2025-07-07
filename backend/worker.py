import os
import json
from datetime import datetime, time
from typing import Any, Dict, List, Optional
from clickhouse_driver import Client
from environments import BACKUP_META_FILE
from logger import logger


class BackupManager:
    def __init__(self, meta_path: str = BACKUP_META_FILE):
        self.meta_path = meta_path
        self.backups = self._load_meta()

    def _load_meta(self) -> List[Dict[str, Any]]:
        if os.path.exists(self.meta_path):
            with open(self.meta_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    def _save_meta(self) -> None:
        with open(self.meta_path, "w", encoding="utf-8") as f:
            json.dump(self.backups, f, indent=2, ensure_ascii=False)

    def add_backup(self, backup_info: Dict[str, Any]) -> None:
        self.backups.append(backup_info)
        self._save_meta()

    def remove_backup(self, backup_id: str) -> bool:
        # Проверка зависимости: нельзя удалить full, если есть incremental с base_backup=backup_id
        backup = self.get_backup(backup_id)
        if not backup:
            logger.debug(f"Бэкап с id={backup_id} не найден")
            return False
        if backup["type"] == "full":
            for b in self.backups:
                if b.get("base_backup") == backup_id:
                    logger.debug(f"Нельзя удалить полный бэкап {backup_id}, есть инкременты, ссылающиеся на него: {b['id']}")
                    return False
        # Удаляем бэкап
        self.backups = [b for b in self.backups if b["id"] != backup_id]
        self._save_meta()
        logger.debug(f"Бэкап {backup_id} удалён из метаданных")
        return True

    def get_backup(self, backup_id: str) -> Optional[Dict[str, Any]]:
        for b in self.backups:
            if b["id"] == backup_id:
                return b
        return None

    def list_backups(self, database: Optional[str] = None) -> List[Dict[str, Any]]:
        if database:
            return [b for b in self.backups if b["database"] == database]
        return self.backups

class ClickHouseBackup:
    def __init__(self, host="localhost", port=9000, user="default", password="", database="default"):
        self.client = Client(host=host, port=port, user=user, password=password, database=database)
        self.meta = BackupManager()

    def wait_for_operation(self, op_id: str, poll_sec: int = 2) -> None:
        while True:
            rows = self.client.execute("SELECT status, error FROM system.backups WHERE id = %(id)s", {"id": op_id})
            if not rows:
                logger.debug(f"⚠️  Операция {op_id} не найдена в system.backups")
                return
            status, error = rows[0]
            if status in ("BACKUP_CREATED", "RESTORED"):
                logger.debug(f"✅ Операция {op_id} завершена со статусом {status}")
                return
            if status in ("BACKUP_FAILED", "RESTORE_FAILED"):
                raise RuntimeError(f"❌ Операция {op_id} провалена: {error}")
            logger.debug(f"⌛ Статус {status}...")
            time.sleep(poll_sec)

    def backup_full(self, database: str, destination: str, async_mode: bool = False) -> None:
        query = f"BACKUP DATABASE {database} TO {destination}"
        if async_mode:
            query += " ASYNC"
        logger.debug(f"Выполняется: {query}")
        op_id, status = self.client.execute(query)[0]
        logger.debug(f"ID операции: {op_id}, статус: {status}")
        if not async_mode:
            self.wait_for_operation(op_id)
        # Записываем метаданные
        self.meta.add_backup({
            "id": op_id,
            "database": database,
            "type": "full",
            "destination": destination,
            "base_backup": None,
            "timestamp": datetime.now().isoformat(),
            "status": status
        })

    def backup_incremental(self, database: str, destination: str, base_backup_id: str, async_mode: bool = False) -> None:
        base_backup = self.meta.get_backup(base_backup_id)
        if not base_backup:
            raise ValueError(f"Базовый бэкап {base_backup_id} не найден в метаданных")
        base_expr = base_backup["destination"]
        query = f"BACKUP DATABASE {database} TO {destination} SETTINGS base_backup = {base_expr}"
        if async_mode:
            query += " ASYNC"
        logger.debug(f"Выполняется: {query}")
        op_id, status = self.client.execute(query)[0]
        logger.debug(f"ID операции: {op_id}, статус: {status}")
        if not async_mode:
            self.wait_for_operation(op_id)
        self.meta.add_backup({
            "id": op_id,
            "database": database,
            "type": "incremental",
            "destination": destination,
            "base_backup": base_backup_id,
            "timestamp": datetime.utcnow().isoformat(),
            "status": status
        })

    def restore(self, database: str, source: str, allow_non_empty: bool = False, async_mode: bool = False) -> None:
        opts = " SETTINGS allow_non_empty_tables=1" if allow_non_empty else ""
        query = f"RESTORE DATABASE {database} FROM {source}{opts}"
        if async_mode:
            query += " ASYNC"
        logger.debug(f"Выполняется: {query}")
        op_id, status = self.client.execute(query)[0]
        logger.debug(f"ID операции: {op_id}, статус: {status}")
        if not async_mode:
            self.wait_for_operation(op_id)

    def list_databases(self) -> List[str]:
        rows = self.client.execute("SHOW DATABASES")
        return [row[0] for row in rows]

    def list_backups(self, database: Optional[str] = None) -> None:
        backups = self.meta.list_backups(database)
        if not backups:
            logger.debug("Бэкапы не найдены")
            return
        for b in backups:
            logger.debug(f"ID: {b['id']}, DB: {b['database']}, Тип: {b['type']}, Дата: {b['timestamp']}, Место: {b['destination']}")

    def delete_backup(self, backup_id: str) -> None:
        # Удаляем из метаданных
        if not self.meta.remove_backup(backup_id):
            return
        # TODO: можно добавить удаление физического файла/объекта, если требуется
        logger.debug(f"Удаление физического бэкапа по id={backup_id} не реализовано, сделайте вручную.")
