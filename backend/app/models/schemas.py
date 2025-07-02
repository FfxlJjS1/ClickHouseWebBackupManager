from pydantic import BaseModel
from typing import List, Optional
from enum import Enum

class BackupType(str, Enum):
    auto = "auto"
    full = "full"
    incremental = "incremental"

class BackupCreateRequest(BaseModel):
    backup_type: BackupType = BackupType.auto

class BackupItem(BaseModel):
    name: str
    type: str
    date: str
    size: Optional[str] = None
    restore_status: Optional[str] = None

class BackupListResponse(BaseModel):
    backups: List[BackupItem]

class OperationResponse(BaseModel):
    status: str
    output: str
    backup_name: Optional[str] = None