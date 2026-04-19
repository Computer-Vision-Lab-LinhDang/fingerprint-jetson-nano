"""Application lifecycle helpers for the Jetson worker."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator

from fastapi import FastAPI

from app.core.config import get_settings
from app.services.pipeline_service import PipelineService
from app.services.sensor_service import SensorService

logger = logging.getLogger(__name__)

_mqtt_client: Any | None = None


async def startup(app: FastAPI | None = None) -> None:
    """Initialize directories, sensor, pipeline, and MQTT connectivity."""
    global _mqtt_client

    settings = get_settings()
    logger.info("=== Fingerprint Jetson Nano Worker starting up ===")
    logger.info("Device ID: %s", settings.device_id)
    logger.info("Inference backend: %s", settings.backend)
    logger.info("Worker home: %s", settings.worker_home)

    for path in (settings.model_dir, settings.data_dir, settings.backup_dir):
        Path(path).mkdir(parents=True, exist_ok=True)
    logger.info("Data directories are ready.")

    try:
        from app.database.database import DatabaseManager

        db_path = str(Path(settings.data_dir) / "fingerprint.db")
        db = DatabaseManager(db_path)
        logger.info("Local database ready: %s", db.db_path)
    except Exception as exc:
        logger.warning("Database init failed: %s (continuing without local DB)", exc)

    sensor = SensorService.get_instance()
    hardware_connected = await sensor.initialize(
        vid=settings.sensor_vid,
        pid=settings.sensor_pid,
        sdk_path=settings.sensor_sdk_path,
        use_mock=settings.mock_mode,
    )
    if settings.mock_mode:
        logger.info("Mock mode enabled; using sample fingerprint images.")
    elif hardware_connected:
        logger.info("USB sensor connected successfully.")
    else:
        logger.warning("USB sensor not found; using mock fallback.")

    pipeline = PipelineService.get_instance()
    await pipeline.initialize()
    logger.info("Inference pipeline ready. Active model: %s", pipeline.active_model)

    if not settings.mqtt_enabled:
        logger.info("MQTT disabled; running in standalone mode")
        logger.info("=== Worker startup complete - listening for requests ===")
        return

    try:
        from app.mqtt.client import get_mqtt_client
        from app.mqtt.handlers import create_message_handler

        _mqtt_client = get_mqtt_client()
        _mqtt_client.set_message_handler(create_message_handler(_mqtt_client))

        logger.info(
            "Connecting to MQTT broker %s:%d ...",
            settings.mqtt_broker_host,
            settings.mqtt_broker_port,
        )
        await asyncio.to_thread(_mqtt_client.connect)
        await asyncio.sleep(2)

        if _mqtt_client.is_connected:
            logger.info("MQTT connected to orchestrator")
        else:
            logger.warning(
                "MQTT connection pending (broker: %s:%d)",
                settings.mqtt_broker_host,
                settings.mqtt_broker_port,
            )
    except Exception as exc:
        logger.warning("MQTT connection failed: %s (running in standalone mode)", exc)
        _mqtt_client = None

    logger.info("=== Worker startup complete - listening for requests ===")


async def shutdown(app: FastAPI | None = None) -> None:
    """Shut down MQTT, pipeline, and sensor cleanly."""
    global _mqtt_client

    logger.info("=== Worker shutting down... ===")

    if _mqtt_client is not None:
        try:
            await asyncio.to_thread(_mqtt_client.disconnect)
            logger.info("MQTT disconnected.")
        except Exception as exc:
            logger.warning("MQTT disconnect error: %s", exc)
        finally:
            _mqtt_client = None

    await PipelineService.get_instance().shutdown()
    await SensorService.get_instance().shutdown()
    logger.info("=== Worker shut down cleanly. ===")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """FastAPI lifespan wrapper for Python 3.10+."""
    await startup(app)
    try:
        yield
    finally:
        await shutdown(app)
