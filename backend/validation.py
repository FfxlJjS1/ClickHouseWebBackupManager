import re

from fastapi import HTTPException

def is_valid_identifier(identifier: str) -> bool:
    """Проверяет валидность идентификатора для ClickHouse"""
    return bool(re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', identifier))

def is_valid_backup_identifier(backup_identifier: str) -> bool:
    """Проверяет валидность идентификатора для бекапа ClickHouse"""
    return bool(re.match(r'^[a-z0-9\-]*$', backup_identifier))

def validate_identifier(identifier: str):
    """Выбрасывает исключение при невалидном идентификаторе"""
    if not is_valid_identifier(identifier):
        raise HTTPException(f"Идентификатов '{identifier}' имеет не верный формат")

def validate_backup_identifier(backup_identifier: str):
    """Выбрасывает исключение при невалидном идентификаторе для бекапа"""
    if not is_valid_backup_identifier(backup_identifier):
        raise HTTPException(status_code=400, detail="base_backup_id имеет не верный формат")
