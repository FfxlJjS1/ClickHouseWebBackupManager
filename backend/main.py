from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
import uuid
import subprocess

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BACKUP_DIR = os.getenv("BACKUP_STORAGE", "/backups")

@app.get("/api/backups")
async def list_backups():
    return [f for f in os.listdir(BACKUP_DIR) if f.endswith('.zip')]

@app.post("/api/backups/create")
async def create_backup(backup_type: str = 'full'):
    backup_id = str(uuid.uuid4())
    backup_path = os.path.join(BACKUP_DIR, f"{backup_id}.zip")
    
    # Асинхронный вызов worker через Celery/RabbitMQ в прод версии
    subprocess.Popen([
        "python", "worker.py", 
        "create", 
        backup_path,
        backup_type
    ])
    
    return {"id": backup_id, "status": "started"}

@app.post("/api/backups/restore/{backup_id}")
async def restore_backup(backup_id: str):
    backup_path = os.path.join(BACKUP_DIR, f"{backup_id}.zip")
    
    if not os.path.exists(backup_path):
        raise HTTPException(status_code=404, detail="Backup not found")
    
    subprocess.Popen([
        "python", "worker.py", 
        "restore", 
        backup_path
    ])
    
    return {"status": "restoration_started"}

@app.delete("/api/backups/{backup_id}")
async def delete_backup(backup_id: str):
    backup_path = os.path.join(BACKUP_DIR, f"{backup_id}.zip")
    
    if os.path.exists(backup_path):
        os.remove(backup_path)
        return {"status": "deleted"}
    else:
        raise HTTPException(status_code=404, detail="Backup not found")