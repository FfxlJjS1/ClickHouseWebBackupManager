from fastapi import APIRouter, HTTPException, status
from app.utils.backup_utils import (
    create_backup, 
    restore_backup, 
    delete_backup, 
    list_backups
)
from app.models.schemas import (
    BackupCreateRequest,
    BackupListResponse,
    OperationResponse
)
from loguru import logger

router = APIRouter()

@router.post("/backups", response_model=OperationResponse, status_code=status.HTTP_201_CREATED)
def create_new_backup(request: BackupCreateRequest):
    try:
        output = create_backup(request.backup_type.value)
        
        # Извлекаем имя созданного бэкапа
        backup_name = None
        if "successfully created" in output:
            for line in output.splitlines():
                if "created backup" in line:
                    backup_name = line.split("'")[1]
                    break
        
        return {
            "status": "success",
            "output": output,
            "backup_name": backup_name
        }
    except Exception as e:
        logger.error(f"Backup creation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/backups/restore/{backup_name}", response_model=OperationResponse)
def restore_from_backup(backup_name: str):
    try:
        output = restore_backup(backup_name)
        return {
            "status": "success",
            "output": output
        }
    except Exception as e:
        logger.error(f"Restore failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.delete("/backups/{backup_name}", response_model=OperationResponse)
def delete_existing_backup(backup_name: str):
    try:
        output = delete_backup(backup_name)
        return {
            "status": "success",
            "output": output
        }
    except Exception as e:
        logger.error(f"Delete failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/backups", response_model=BackupListResponse)
def get_backup_list():
    try:
        backups = list_backups()
        return {"backups": backups}
    except Exception as e:
        logger.error(f"Backup listing failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
