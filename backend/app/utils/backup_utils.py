import subprocess
import os
import re
from datetime import datetime
from loguru import logger
from app.core.config import settings

def run_script(script_name: str, args: list = None) -> str:
    """Выполняет shell-скрипт и возвращает результат"""
    script_path = os.path.join(settings.BACKUP_SCRIPTS_DIR, script_name)
    if not os.path.exists(script_path):
        raise FileNotFoundError(f"Script {script_path} not found")
    
    cmd = [script_path]
    if args:
        cmd.extend(args)
    
    logger.info(f"Executing: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        logger.error(f"Script failed: {e.stderr}")
        raise RuntimeError(f"Script failed: {e.stderr}") from e

def create_backup(backup_type: str = "auto") -> str:
    """Создает бэкап указанного типа"""
    return run_script("create_backup.sh", [backup_type])

def restore_backup(backup_name: str) -> str:
    """Восстанавливает базу из указанного бэкапа"""
    return run_script("restore_backup.sh", [backup_name])

def delete_backup(backup_name: str) -> str:
    """Удаляет указанный бэкап"""
    try:
        result = subprocess.run(
            ["clickhouse-backup", "delete", backup_name],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Delete failed: {e.stderr}") from e

def list_backups() -> list:
    """Возвращает список доступных бэкапов"""
    try:
        # Создаем переменные окружения для подключения
        env = os.environ.copy()
        env.update({
            'CLICKHOUSE_HOST': settings.CLICKHOUSE_HOST,
            'CLICKHOUSE_PORT': str(settings.CLICKHOUSE_PORT),
            'CLICKHOUSE_USER': settings.CLICKHOUSE_USER,
            'CLICKHOUSE_PASSWORD': settings.CLICKHOUSE_PASSWORD
        })
        
        logger.info(f"Connecting to ClickHouse at {settings.CLICKHOUSE_HOST}:{settings.CLICKHOUSE_PORT}")
        
        result = subprocess.run(
            [
                "clickhouse-backup", "list"
            ],
            capture_output=True,
            text=True,
            check=True,
            env=env  # Передаем переменные окружения
        )
        
        return parse_backup_list(result.stdout)
        
    except subprocess.CalledProcessError as e:
        logger.error(f"List failed. Command output: {e.stdout}, Error: {e.stderr}")
        raise RuntimeError(f"List failed: {e.stderr}") from e

def parse_backup_list(output: str) -> list:
    """Парсит вывод команды list в структурированный список"""
    backups = []
    for line in output.splitlines()[1:]:  # Пропускаем заголовок
        if not line.strip():
            continue
            
        parts = line.split()
        if not parts:
            continue
            
        backup_name = parts[0]
        size = parts[1] if len(parts) > 1 else None
        
        # Определяем тип и дату бэкапа
        backup_type, formatted_date = classify_backup(backup_name)
            
        backups.append({
            "name": backup_name,
            "type": backup_type,
            "date": formatted_date,
            "size": size
        })
        
    return backups

def classify_backup(backup_name: str) -> tuple:
    """Определяет тип бэкапа и дату"""
    if backup_name.startswith("full_"):
        backup_type = "full"
    elif backup_name.startswith("inc_"):
        backup_type = "incremental"
    else:
        backup_type = "unknown"
    
    # Извлекаем дату из имени
    date_match = re.search(r"\d{8}", backup_name)
    date_str = date_match.group(0) if date_match else "unknown"
    
    try:
        date_obj = datetime.strptime(date_str, "%Y%m%d")
        formatted_date = date_obj.strftime("%Y-%m-%d")
    except ValueError:
        formatted_date = date_str
    
    return backup_type, formatted_date
