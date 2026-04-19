"""Sensor endpoints and real-time fingerprint preview streaming."""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import time

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from app.api.schemas import ApiResponse, CaptureResponse, LEDRequest, SensorStatus
from app.services.sensor_service import SensorService, get_sensor_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sensor", tags=["sensor"])


@router.get("/status", response_model=ApiResponse)
async def sensor_status(
    sensor: SensorService = Depends(get_sensor_service),
) -> ApiResponse:
    info = await sensor.get_info()
    user_count = await sensor.get_user_count()
    compare_level = await sensor.get_compare_level()

    data = SensorStatus(
        connected=sensor.is_connected,
        vendor_id=info.vendor_id if info else None,
        product_id=info.product_id if info else None,
        firmware_version=None,
        serial_number=None,
        resolution_dpi=info.resolution_dpi if info else None,
        user_count=user_count if user_count >= 0 else None,
        compare_level=compare_level if compare_level >= 0 else None,
        is_real_hardware=sensor.is_real_hardware,
    )
    return ApiResponse(success=True, data=data)


@router.post("/capture", response_model=ApiResponse)
async def capture(
    sensor: SensorService = Depends(get_sensor_service),
) -> ApiResponse:
    result = await sensor.capture_image()

    if not result.success:
        return ApiResponse(
            success=False,
            data=CaptureResponse(
                success=False,
                image_base64="",
                width=0,
                height=0,
                quality_score=0.0,
                message=result.error,
            ),
            error=result.error,
        )

    return ApiResponse(
        success=True,
        data=CaptureResponse(
            success=True,
            image_base64=base64.b64encode(result.image_data).decode("ascii"),
            width=result.width,
            height=result.height,
            quality_score=result.quality_score,
            has_finger=result.has_finger,
            message="Capture successful",
        ),
    )


@router.post("/led", response_model=ApiResponse)
async def led_control(
    body: LEDRequest,
    sensor: SensorService = Depends(get_sensor_service),
) -> ApiResponse:
    if body.color in {"off", "0"}:
        ok = await sensor.led_off()
    else:
        color_map = {"red": 1, "green": 2, "blue": 4, "white": 7}
        try:
            color_int = int(body.color)
        except ValueError:
            color_int = color_map.get(body.color, 0)
        ok = await sensor.led_on(color_int)

    return ApiResponse(
        success=ok,
        data={"color": body.color, "duration_ms": body.duration_ms},
    )


@router.websocket("/stream")
async def ws_sensor_stream(websocket: WebSocket) -> None:
    """Stream live fingerprint frames over WebSocket."""
    await websocket.accept()
    logger.info("WebSocket /sensor/stream connected")

    sensor = SensorService.get_instance()
    streaming = False
    target_fps = 10
    stream_task: asyncio.Task[None] | None = None

    async def _stream_loop() -> None:
        nonlocal streaming
        while streaming:
            result = await sensor.capture_image()
            if result.success:
                await websocket.send_json(
                    {
                        "type": "frame",
                        "image_base64": base64.b64encode(result.image_data).decode("ascii"),
                        "width": result.width,
                        "height": result.height,
                        "quality_score": result.quality_score,
                        "has_finger": result.has_finger,
                        "timestamp": time.time(),
                    }
                )
            await asyncio.sleep(1.0 / target_fps)

    try:
        while True:
            raw_message = await websocket.receive_text()
            try:
                message = json.loads(raw_message)
            except json.JSONDecodeError:
                await websocket.send_json({"error": "Invalid JSON"})
                continue

            action = str(message.get("action", "")).lower()
            if action == "start":
                target_fps = max(1, min(int(message.get("fps", 10)), 30))
                streaming = True
                if stream_task is None or stream_task.done():
                    stream_task = asyncio.create_task(_stream_loop())
                await websocket.send_json({"status": "streaming", "fps": target_fps})
                continue

            if action == "stop":
                streaming = False
                if stream_task and not stream_task.done():
                    stream_task.cancel()
                    try:
                        await stream_task
                    except asyncio.CancelledError:
                        pass
                stream_task = None
                await websocket.send_json({"status": "stopped"})
                continue

            await websocket.send_json({"error": f"Unknown action: {action}"})
    except WebSocketDisconnect:
        logger.info("WebSocket /sensor/stream disconnected")
    except Exception as exc:
        logger.exception("WebSocket /sensor/stream error: %s", exc)
        try:
            await websocket.close(code=1011, reason=str(exc))
        except Exception:
            pass
    finally:
        streaming = False
        if stream_task and not stream_task.done():
            stream_task.cancel()
            try:
                await stream_task
            except asyncio.CancelledError:
                pass
