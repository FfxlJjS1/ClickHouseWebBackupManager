import shutil
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import os
from datetime import datetime

from pydantic import BaseModel, constr

from validation import validate_backup_identifier, validate_identifier
from worker import ClickHouseBackup
from environments import BACKUP_DIR, CLICKHOUSE_HOST, CLICKHOUSE_PORT, CLICKHOUSE_USER, CLICKHOUSE_PASSWORD, CLICKHOUSE_DB


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

# --- Pydantic модели для запросов и ответов --- #

class BackupCreateRequest(BaseModel):
    database: str
    backup_type: str = "full"  # full или incremental
    base_backup_id: Optional[str] = None  # для incremental
    async_mode: bool = False
    description: Optional[str] = None

class BackupRestoreRequest(BaseModel):
    database: str
    backup_id: str
    async_mode: bool = False

class BackupInfo(BaseModel):
    id: str
    database: str
    type: str
    destination: str
    base_backup: Optional[str]
    timestamp: str
    status: str
    description: Optional[str] = None

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
    validate_identifier(database)
    
    backups = chb.meta.list_backups(database)
    return backups

@app.post("/api/backups", response_model=BackupInfo)
async def create_backup(req: BackupCreateRequest):
    """
    Создать бэкап (full или incremental).
    """
    validate_identifier(req.database)
    validate_identifier(req.backup_type)

    if req.backup_type not in ("full", "incremental"):
        raise HTTPException(status_code=400, detail="backup_type должен быть 'full' или 'incremental'")
    
    # Автоматически генерируем путь для бэкапа
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(BACKUP_DIR, req.database, req.backup_type, f"backup_{timestamp}")
    destination = f"File('{backup_path}')"

    if req.backup_type == "full":
        chb.backup_full(
            database=req.database,
            destination=destination,
            async_mode=req.async_mode,
            description=req.description
        )
    else:
        if not req.base_backup_id:
            raise HTTPException(status_code=400, detail="base_backup_id обязателен для incremental бэкапа")

        chb.backup_incremental(
            database=req.database,
            destination=destination,
            base_backup_id=req.base_backup_id,
            async_mode=req.async_mode,
            description=req.description
        )

    # Возвращаем последний добавленный бэкап (предполагается, что add_backup вызывается внутри методов)
    backups = chb.meta.list_backups(req.database)
    return backups[-1]

@app.post("/api/backups/restore")
async def restore_backup(req: BackupRestoreRequest):
    """
    Восстановить базу из бэкапа по его ID.
    """
    validate_identifier(req.database)
    validate_backup_identifier(req.backup_id)

    # Получаем информацию о бэкапе по ID
    backup_info = chb.meta.get_backup(req.backup_id)
    if not backup_info:
        raise HTTPException(
            status_code=404,
            detail=f"Бэкап с ID {req.backup_id} не найден"
        )
    
    # Извлекаем путь из destination
    source = backup_info["destination"]

    try:
        chb.restore(
            database=req.database,
            source=source,
            async_mode=req.async_mode
        )
        return {"status": "restoration_started"}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка восстановления: {str(e)}"
        )

@app.delete("/api/backups/{backup_id}")
async def delete_backup(backup_id: str):
    """
    Удалить бэкап по ID с проверкой зависимостей.
    """
    validate_backup_identifier(backup_id)

    # Удаляем из метаданных и получаем информацию о бекапе
    backup_info = chb.meta.remove_backup(backup_id)
    
    if backup_info is None:
        raise HTTPException(
            status_code=400, 
            detail="Нельзя удалить бэкап: есть зависимости или не найден"
        )
    
    # Извлекаем путь из destination (формат: "File('/path/to/backup')")
    destination = backup_info["destination"]
    if destination.startswith("File('") and destination.endswith("')"):
        backup_path = destination[6:-2]  # Убираем "File('" и "')"
        
        try:
            # Проверяем существование пути
            if os.path.exists(backup_path):
                # Рекурсивно удаляем директорию
                shutil.rmtree(backup_path)
                return {"status": "deleted", "path": backup_path}
            else:
                return {"status": "deleted_meta", "detail": f"Физический бэкап не найден: {backup_path}"}
        except Exception as e:
            return {"status": "deleted_meta", "detail": f"Ошибка удаления физического бэкапа: {str(e)}"}
    
    return {"status": "deleted_meta", "detail": "Физическое удаление не поддерживается для этого типа бекапа"}
