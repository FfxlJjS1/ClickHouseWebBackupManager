from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import os

from pydantic import BaseModel

from worker import ClickHouseBackup
from environments import CLICKHOUSE_HOST, CLICKHOUSE_PORT, CLICKHOUSE_USER, CLICKHOUSE_PASSWORD, CLICKHOUSE_DB


app = FastAPI(title="ClickHouse Backup Manager API")

chb = ClickHouseBackup(
    host=CLICKHOUSE_HOST,
    port=CLICKHOUSE_PORT,
    user=CLICKHOUSE_USER,
    password=CLICKHOUSE_PASSWORD,
    database=CLICKHOUSE_DB
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BACKUP_DIR = os.getenv("BACKUP_STORAGE", "/backups")

# --- Pydantic модели для запросов и ответов --- #

class BackupCreateRequest(BaseModel):
    database: str
    destination: str
    backup_type: str = "full"  # full или incremental
    base_backup_id: Optional[str] = None  # для incremental
    async_mode: bool = False

class BackupRestoreRequest(BaseModel):
    database: str
    source: str
    allow_non_empty: bool = False
    async_mode: bool = False

class BackupInfo(BaseModel):
    id: str
    database: str
    type: str
    destination: str
    base_backup: Optional[str]
    timestamp: str
    status: str

# --- Эндпоинты --- #

@app.get("/api/databases", response_model=List[str])
async def list_databases():
    """
    Получить список баз данных ClickHouse.
    """
    return chb.list_databases()

@app.get("/api/backups", response_model=List[BackupInfo])
async def list_backups(database: Optional[str] = Query(None, description="Фильтр по базе")):
    """
    Получить список бэкапов, опционально отфильтрованных по базе.
    """
    backups = chb.meta.list_backups(database)
    return backups

@app.post("/api/backups", response_model=BackupInfo)
async def create_backup(req: BackupCreateRequest):
    """
    Создать бэкап (full или incremental).
    """
    if req.backup_type not in ("full", "incremental"):
        raise HTTPException(status_code=400, detail="backup_type должен быть 'full' или 'incremental'")

    if req.backup_type == "full":
        chb.backup_full(req.database, req.destination, async_mode=req.async_mode)
    else:
        if not req.base_backup_id:
            raise HTTPException(status_code=400, detail="base_backup_id обязателен для incremental бэкапа")
        chb.backup_incremental(req.database, req.destination, req.base_backup_id, async_mode=req.async_mode)

    # Возвращаем последний добавленный бэкап (предполагается, что add_backup вызывается внутри методов)
    backups = chb.meta.list_backups(req.database)
    return backups[-1]

@app.post("/api/backups/restore")
async def restore_backup(req: BackupRestoreRequest):
    """
    Восстановить базу из бэкапа.
    """
    chb.restore(req.database, req.source, allow_non_empty=req.allow_non_empty, async_mode=req.async_mode)
    return {"status": "restoration_started"}

@app.delete("/api/backups/{backup_id}")
async def delete_backup(backup_id: str):
    """
    Удалить бэкап по ID с проверкой зависимостей.
    """
    success = chb.meta.remove_backup(backup_id)
    if not success:
        raise HTTPException(status_code=400, detail="Нельзя удалить бэкап: есть зависимости или не найден")
    # TODO: здесь можно добавить удаление физического файла/объекта, если требуется
    return {"status": "deleted"}
