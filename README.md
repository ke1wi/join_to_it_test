# WebSocket Notification Server

A production-ready FastAPI WebSocket notification service with:

- Real-time WebSocket notifications
- Connection tracking & broadcast
- Background periodic system messages
- **Advanced graceful shutdown** compatible with:
  - uvicorn CLI
  - Docker SIGTERM
  - systemd
  - multiple uvicorn workers
- Fully tested using `pytest` (unit + integration tests)
- Clean architecture with modular components

This project is self-contained and runnable with:

```bash
uvicorn src.main:app
```
---

## 🚀 Features

- WebSocket Endpoint (/ws)
- Clients connect via WebSocket
- Assigned a unique client_id
- Server tracks all active connections
- Supports:
- personal messages
- broadcast messages
- system notifications every N seconds

✔ Graceful Shutdown (Key Feature)

The server does not stop immediately on SIGINT/SIGTERM.

Instead: 
  1. Stops accepting new WebSocket connections
  2. Waits until all clients disconnect OR
  3. Forces disconnect after 30 minutes (configurable)
  4. Only then gives the signal back to uvicorn to terminate safely

This ensures:
• zero message loss
• clean client disconnect
• avoids uvicorn killing sockets prematurely

✔ Multi-Worker Friendly

Each worker handles shutdown independently.

✔ Test Suite Included
• WebSocket integration tests
• ConnectionManager unit tests
• Graceful shutdown behaviour tests

Run:

```bash
pytest
```

---

## 📂 Project Structure
```
src/
├── main.py # FastAPI app + signal handler initialization
├── connection_manager.py # Tracks active WebSocket connections
├── signal_handler.py # Custom pre-uvicorn signal interception
├── utils.py # Notification loop + graceful shutdown logic
├── routers/
│ ├── websocket.py # /ws endpoint implementation
│ └── rest.py # Optional REST endpoints (/status, etc.)
└── config.py # Config values (timeouts, constants)

tests/
├── test_connection_manager.py
├── test_graceful_shutdown.py
├── test_websocket_routes.py
└── helpers/fake_websocket.py
```
---

## ⚙️ Installation

1. Clone

```bash
git clone https://github.com/ke1wi/join_to_it_test.git
cd join_to_it_test
```

2. Install dependencies

Using Rye (recommended):

```bash
rye sync
```

Or classic:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.lock
```

---

## ▶️ Running the Server

Development mode:

```bash
uvicorn src.main:app --reload
```

Production mode:

```bash
uvicorn src.main:app --host 0.0.0.0 --port 8000
```

Multi-worker (each worker gracefully shutdowns independently):

```bash
uvicorn src.main:app --workers 4
```

---

## 🧪 Testing the WebSocket Endpoint

Using browser console:

```js
const ws = new WebSocket("ws://localhost:8000/ws");

ws.onopen = () => console.log("connected");
ws.onmessage = (e) => console.log(">", e.data);
ws.onclose = () => console.log("closed");
```

You will receive periodic system messages like:

[System] Periodic notification #1 – Active clients: 1

Using wscat:

```bash
npm install -g wscat
wscat -c ws://localhost:8000/ws
```

Or Use Postman

---

## 🧵 REST Endpoints (Optional)

GET /status

Returns active clients and server metadata.

POST /broadcast

Broadcasts a message to all WebSocket clients.

---

## 🛑 Graceful Shutdown Explained

This project implements an enhanced signal handler that overrides uvicorn’s default behavior.

## 🔄 Default uvicorn behavior:
• When you press Ctrl+C or send SIGTERM →
uvicorn kills all WebSockets immediately

This breaks graceful shutdown.

## 🚀 Our custom behavior: 1. Intercept SIGINT/SIGTERM before uvicorn handles it 2. Start graceful shutdown:
• stop accepting new WebSocket connections
• wait until all clients disconnect
• OR force close after timeout (default 30 min) 3. After cleanup:
• restore original uvicorn signal handlers
• send SIGINT/SIGTERM back to uvicorn via os.kill() 4. uvicorn performs its normal shutdown cycle cleanly

## 💥 Force shutdown

If user presses Ctrl+C 3 times → shutdown is forced immediately
(configurable via AMOUNT_OF_SIGNALS_TO_FORCE_SHUTDOWN).

---

## 🧪 Running Tests

Run all tests:

pytest

Includes:
• Unit tests for ConnectionManager
• Tests for forced + graceful shutdown behaviour
• WebSocket integration tests via TestClient

---

## 🐳 Docker Support (optional)

Create Dockerfile:

```Dockerfile
FROM python:3.11

WORKDIR /app
COPY . .

RUN pip install -r requirements.lock

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build:

```bash
docker build -t websocket-server .
docker run -p 8000:8000 websocket-server
```

Graceful shutdown will work with Docker’s SIGTERM.

---

## 📝 Configuration

Edit values in src/config.py:

```python
AMOUNT_OF_SIGNALS_TO_FORCE_SHUTDOWN = 3
CLEANUP_INTERVAL = 60
NOTIFICATION_INTERVAL = 10
NOTIFICATION_MESSAGE_STRIP = 50
POLLING_INTERVAL = 2
TIME_TO_WAIT_FOR_SHUTDOWN = 30 * 60 # 30 minutes
```

---

## 🎯 Summary

This project delivers:
- Full-featured WebSocket notification service
- Robust graceful shutdown (safe for production)
- Clean architecture
- Proper signal handling (uvicorn-compatible)
- Test coverage
- Ready for Docker, Kubernetes, and multi worker deployments
