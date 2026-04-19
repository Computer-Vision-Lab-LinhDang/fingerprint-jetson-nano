# fingerprint-jetson-nano

Installable fingerprint worker for Jetson-based nodes.

The worker now targets Python 3.10+, keeps the existing sensor/MQTT/pipeline flow, and adds WebSocket compatibility for the teammate verify demo.

## Install

```bash
cd fingerprint-jetson-nano
python3.10 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install --upgrade setuptools wheel
python -m pip install --no-build-isolation .[gui]
```

Optional extras:

```bash
python -m pip install --no-build-isolation .[onnx]
python -m pip install --no-build-isolation .[faiss]
python -m pip install --no-build-isolation .[dev]
```

## Run

Start the API:

```bash
fingerprint-worker-api
```

Start the desktop GUI:

```bash
fingerprint-worker-gui
```

Start the interactive CLI:

```bash
fingerprint-worker-cli
```

## Configuration

Copy `.env.example` to `.env` and adjust the values you need.

Important paths are resolved relative to `WORKER_HOME` when they are not absolute:

- `WORKER_HOME`
- `WORKER_MODEL_DIR`
- `WORKER_DATA_DIR`
- `WORKER_BACKUP_DIR`
- `WORKER_MODEL_PATH`

## Verify Demo Compatibility

The worker exposes both the existing API routes and the demo-compatible WebSocket routes:

- `POST /api/v1/verify`
- `POST /api/v1/identify`
- `WS /api/v1/ws/verification`
- `WS /api/v1/ws/verify`
- `WS /ws/verification`
- `WS /ws/verify`

The demo protocol supports:

- `{"action":"start","mode":"verify","user_id":"123"}`
- `{"action":"start","mode":"identify","top_k":5}`
- `{"action":"stop"}`

While streaming, the worker sends `capture_preview`, `verification_result`, and `identification_result` messages.
