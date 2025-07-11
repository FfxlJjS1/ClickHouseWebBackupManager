import pytest
import httpx
from clickhouse_driver import Client
import os
from datetime import datetime
import asyncio

# Общие настройки
API_URL = "http://backend:8000/api"
CLICKHOUSE_HOST = "clickhouse"
CLICKHOUSE_PORT = 9000
CLICKHOUSE_USER = "admin"
CLICKHOUSE_PASSWORD = "password"
TEST_DB_PREFIX = "test_db_"

@pytest.fixture(scope="session")
def ch_client():
    client = Client(
        host=CLICKHOUSE_HOST,
        port=CLICKHOUSE_PORT,
        user=CLICKHOUSE_USER,
        password=CLICKHOUSE_PASSWORD
    )
    yield client
    client.disconnect()

@pytest.fixture(scope="function")
def test_db(ch_client):
    """Создает временную БД для теста"""
    db_name = f"{TEST_DB_PREFIX}{datetime.now().strftime('%H%M%S%f')}"
    ch_client.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
    yield db_name
    
    # Удаление после теста
    try:
        ch_client.execute(f"DROP DATABASE IF EXISTS {db_name} SYNC")
    except Exception as e:
        print(f"Error dropping test database: {e}")

@pytest.fixture(scope="function")
def test_table(ch_client, test_db):
    """Создает тестовую таблицу"""
    table_name = "test_table"
    ch_client.execute(f"""
        CREATE TABLE IF NOT EXISTS {test_db}.{table_name} (
            id Int32,
            data String
        ) ENGINE = MergeTree()
        ORDER BY id
    """)
    yield table_name

@pytest.fixture(scope="function")
async def api_client():
    """Клиент для работы с API"""
    async with httpx.AsyncClient(base_url=API_URL, timeout=30.0) as client:
        yield client
