import pytest
import httpx
import time
import json
import os
from datetime import datetime

# Тестовые данные
TEST_DB_PREFIX = "test_db_"

@pytest.mark.asyncio
async def test_database_list(api_client, ch_client, test_db):
    """Проверка получения списка баз данных"""
    # Получаем список баз данных через API
    response = await api_client.get("/databases")
    assert response.status_code == 200
    databases = response.json()
    
    # Проверяем наличие тестовой БД и системных БД
    assert test_db in databases
    assert "system" in databases
    assert "default" in databases

@pytest.mark.asyncio
async def test_backup_full_cycle(api_client, ch_client, test_db, test_table):
    """Полный цикл: создание, восстановление, удаление бекапов"""
    # Добавляем тестовые данные
    ch_client.execute(f"INSERT INTO {test_db}.{test_table} VALUES", [(1, 'alpha'), (2, 'beta')])
    
    # Создаем полный бекап
    backup_data = {
        "database": test_db,
        "backup_type": "full",
        "async_mode": False
    }
    response = await api_client.post("/backups", json=backup_data)
    assert response.status_code == 200
    full_backup = response.json()
    assert full_backup["type"] == "full"
    assert full_backup["status"] == "BACKUP_CREATED"
    
    # Проверяем наличие файлов бекапа
    backup_path = full_backup["destination"][6:-2]  # Извлекаем путь из File('...')
    assert os.path.exists(backup_path)
    
    # Добавляем новые данные
    ch_client.execute(f"INSERT INTO {test_db}.{test_table} VALUES", [(3, 'gamma')])
    
    # Создаем инкрементный бекап
    backup_data = {
        "database": test_db,
        "backup_type": "incremental",
        "base_backup_id": full_backup["id"],
        "async_mode": False
    }
    response = await api_client.post("/backups", json=backup_data)
    assert response.status_code == 200
    inc_backup = response.json()
    assert inc_backup["type"] == "incremental"
    assert inc_backup["base_backup"] == full_backup["id"]
    
    # Проверяем наличие файлов инкрементного бекапа
    inc_backup_path = inc_backup["destination"][6:-2]
    assert os.path.exists(inc_backup_path)
    
    # Повреждаем данные (удаляем все)
    ch_client.execute(f"TRUNCATE TABLE {test_db}.{test_table} SYNC")
    
    # Восстанавливаем из полного бекапа
    restore_data = {
        "database": test_db,
        "backup_id": full_backup["id"],
        "async_mode": False
    }
    response = await api_client.post("/backups/restore", json=restore_data)
    assert response.status_code == 200
    
    # Проверяем восстановленные данные
    result = ch_client.execute(f"SELECT * FROM {test_db}.{test_table} ORDER BY id")
    assert result == [(1, 'alpha'), (2, 'beta')]  # Данные после инкремента не должны быть
    
    # Восстанавливаем из инкрементного бекапа
    restore_data["backup_id"] = inc_backup["id"]
    response = await api_client.post("/backups/restore", json=restore_data)
    assert response.status_code == 200
    
    # Проверяем полное восстановление
    result = ch_client.execute(f"SELECT * FROM {test_db}.{test_table} ORDER BY id")
    assert result == [(1, 'alpha'), (2, 'beta'), (3, 'gamma')]
    
    # Проверяем список бекапов
    response = await api_client.get(f"/backups?database={test_db}")
    assert response.status_code == 200
    backups = response.json()
    assert len(backups) == 2
    assert {b["type"] for b in backups} == {"full", "incremental"}
    
    # Удаляем инкрементный бекап
    response = await api_client.delete(f"/backups/{inc_backup['id']}")
    assert response.status_code == 200
    
    # Проверяем физическое удаление
    assert not os.path.exists(inc_backup_path)
    
    # Пытаемся удалить базовый бекап (должно не получиться из-за зависимостей)
    response = await api_client.delete(f"/backups/{full_backup['id']}")
    assert response.status_code == 400
    
    # Проверяем, что базовый бекап еще существует
    assert os.path.exists(backup_path)

@pytest.mark.asyncio
async def test_multiple_databases(api_client, ch_client, test_db):
    """Проверка независимости бекапов разных баз данных"""
    # Создаем вторую тестовую базу
    db2 = f"{TEST_DB_PREFIX}second_{datetime.now().strftime('%H%M%S%f')}"
    ch_client.execute(f"CREATE DATABASE IF NOT EXISTS {db2}")
    
    try:
        # Создаем бекап для первой базы
        backup_data1 = {"database": test_db, "backup_type": "full"}
        response1 = await api_client.post("/backups", json=backup_data1)
        assert response1.status_code == 200
        
        # Создаем бекап для второй базы
        backup_data2 = {"database": db2, "backup_type": "full"}
        response2 = await api_client.post("/backups", json=backup_data2)
        assert response2.status_code == 200
        
        # Проверяем независимость бекапов
        response = await api_client.get(f"/backups?database={test_db}")
        backups_db1 = response.json()
        assert len(backups_db1) == 1
        assert backups_db1[0]["database"] == test_db
        
        response = await api_client.get(f"/backups?database={db2}")
        backups_db2 = response.json()
        assert len(backups_db2) == 1
        assert backups_db2[0]["database"] == db2
        
    finally:
        # Очистка
        ch_client.execute(f"DROP DATABASE IF EXISTS {db2} SYNC")

@pytest.mark.asyncio
async def test_backup_validation(api_client):
    """Проверка валидации недопустимых имен"""
    invalid_names = [
        "test; DROP TABLE users;--",
        "../../etc/passwd",
        "`rm -rf /`",
        "test$db",
        "invalid name with spaces",
        "' OR 1=1; --"
    ]
    
    for name in invalid_names:
        # Проверка получения списка бекапов
        response = await api_client.get(f"/backups?database={name}")
        assert response.status_code == 400
        
        # Проверка создания бекапа
        backup_data = {
            "database": name,
            "backup_type": "full"
        }
        response = await api_client.post("/backups", json=backup_data)
        assert response.status_code == 400
        
        # Проверка восстановления
        restore_data = {
            "database": name,
            "backup_id": "valid-id"
        }
        response = await api_client.post("/backups/restore", json=restore_data)
        assert response.status_code == 400

@pytest.mark.asyncio
async def test_backup_dependencies(api_client, ch_client, test_db):
    """Проверка зависимостей между бекапами"""
    # Создаем цепочку бекапов
    backup_data = {
        "database": test_db,
        "backup_type": "full",
        "async_mode": False
    }
    response = await api_client.post("/backups", json=backup_data)
    assert response.status_code == 200
    full_backup = response.json()
    
    backup_data["backup_type"] = "incremental"
    backup_data["base_backup_id"] = full_backup["id"]
    response = await api_client.post("/backups", json=backup_data)
    assert response.status_code == 200
    inc_backup1 = response.json()
    
    response = await api_client.post("/backups", json=backup_data)
    assert response.status_code == 200
    inc_backup2 = response.json()
    
    # Пытаемся удалить базовый бекап (должна быть ошибка)
    response = await api_client.delete(f"/backups/{full_backup['id']}")
    assert response.status_code == 400
    
    # Удаляем первый инкрементный
    response = await api_client.delete(f"/backups/{inc_backup1['id']}")
    assert response.status_code == 200
    
    # Базовый все еще нельзя удалить
    response = await api_client.delete(f"/backups/{full_backup['id']}")
    assert response.status_code == 400
    
    # Удаляем второй инкрементный
    response = await api_client.delete(f"/backups/{inc_backup2['id']}")
    assert response.status_code == 200
    
    # Теперь базовый можно удалить
    response = await api_client.delete(f"/backups/{full_backup['id']}")
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_async_backup(api_client, ch_client, test_db, test_table):
    """Проверка асинхронных операций"""
    # Добавляем тестовые данные
    ch_client.execute(f"INSERT INTO {test_db}.{test_table} VALUES", [(1, 'async_test')])
    
    # Создаем асинхронный бекап
    backup_data = {
        "database": test_db,
        "backup_type": "full",
        "async_mode": True
    }
    response = await api_client.post("/backups", json=backup_data)
    assert response.status_code == 200
    backup = response.json()
    
    # Ждем завершения (максимум 30 секунд)
    timeout = 30
    start = time.time()
    while time.time() - start < timeout:
        response = await api_client.get(f"/backups?database={test_db}")
        backups = response.json()
        if backups and backups[0]["status"] == "BACKUP_CREATED":
            break
        await asyncio.sleep(1)
    else:
        pytest.fail("Backup didn't complete in time")
    
    # Проверяем статус
    assert backups[0]["status"] == "BACKUP_CREATED"
    
    # Проверяем восстановление
    ch_client.execute(f"TRUNCATE TABLE {test_db}.{test_table} SYNC")
    
    restore_data = {
        "database": test_db,
        "backup_id": backup["id"],
        "async_mode": True
    }
    response = await api_client.post("/backups/restore", json=restore_data)
    assert response.status_code == 200
    
    # Ждем завершения восстановления
    start = time.time()
    while time.time() - start < timeout:
        result = ch_client.execute(f"SELECT count() FROM {test_db}.{test_table}")
        if result and result[0][0] > 0:
            break
        await asyncio.sleep(1)
    else:
        pytest.fail("Restore didn't complete in time")
    
    # Проверяем данные
    result = ch_client.execute(f"SELECT * FROM {test_db}.{test_table}")
    assert result == [(1, 'async_test')]

@pytest.mark.asyncio
async def test_backup_metadata(api_client, ch_client, test_db):
    """Проверка метаданных бекапов"""
    # Создаем бекап
    backup_data = {"database": test_db, "backup_type": "full"}
    response = await api_client.post("/backups", json=backup_data)
    assert response.status_code == 200
    backup = response.json()
    
    # Проверяем метаданные в ответе
    assert "id" in backup
    assert "database" in backup and backup["database"] == test_db
    assert "type" in backup and backup["type"] == "full"
    assert "destination" in backup
    assert "timestamp" in backup
    assert "status" in backup
    
    # Проверяем формат timestamp
    try:
        datetime.fromisoformat(backup["timestamp"])
    except ValueError:
        pytest.fail("Invalid timestamp format")

@pytest.mark.asyncio
async def test_incremental_without_base(api_client, ch_client, test_db):
    """Проверка создания инкрементного бекапа без базового"""
    # Пытаемся создать инкрементный бекап без указания базового
    backup_data = {
        "database": test_db,
        "backup_type": "incremental",
        "async_mode": False
    }
    response = await api_client.post("/backups", json=backup_data)
    assert response.status_code == 400
    assert "base_backup_id" in response.text

@pytest.mark.asyncio
async def test_restore_nonexistent_backup(api_client, test_db):
    """Проверка восстановления из несуществующего бекапа"""
    restore_data = {
        "database": test_db,
        "backup_id": "nonexistent-backup-id",
        "async_mode": False
    }
    response = await api_client.post("/backups/restore", json=restore_data)
    assert response.status_code == 404
    assert "не найден" in response.text

@pytest.mark.asyncio
async def test_delete_nonexistent_backup(api_client):
    """Проверка удаления несуществующего бекапа"""
    response = await api_client.delete("/backups/nonexistent-backup-id")
    assert response.status_code == 400
    assert "нельзя удалить" in response.text

@pytest.mark.asyncio
async def test_backup_invalid_type(api_client, test_db):
    """Проверка создания бекапа с недопустимым типом"""
    backup_data = {
        "database": test_db,
        "backup_type": "invalid_type",
        "async_mode": False
    }
    response = await api_client.post("/backups", json=backup_data)
    assert response.status_code == 400
    assert "должен быть" in response.text
