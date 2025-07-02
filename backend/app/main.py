from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from app.core.config import settings
from app.api import backups, health

app = FastAPI(
    title="ClickHouse Backup Manager API",
    description="API for managing ClickHouse database backups",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Включаем роутеры
app.include_router(health.router, prefix="/api")
app.include_router(backups.router, prefix="/api/backups")

@app.on_event("startup")
async def startup_event():
    logger.info("Starting ClickHouse Backup Manager")
    logger.info(f"ClickHouse host: {settings.CLICKHOUSE_HOST}:{settings.CLICKHOUSE_PORT}")
    logger.info(f"Backup retention: {settings.BACKUP_RETENTION_DAYS} days")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down ClickHouse Backup Manager")
