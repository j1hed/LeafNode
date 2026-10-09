# LeafNode

FastAPI backend for greenhouse monitoring, plant-care recommendations, user authentication, and ESP32/Jetson integration.

## Run locally

Create a Python environment and install requirements.txt. Copy .env.example to .env and configure your AI provider and optional service keys.

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

API documentation: http://127.0.0.1:8000/docs

Register through POST /api/auth/register and log in through POST /api/auth/login. Use the returned bearer token for protected recommendation and control endpoints.

## Firmware configuration

For each ESP32 sketch, copy its matching *_secrets.h.example file to *_secrets.h and fill in Wi-Fi credentials. Local secret headers are ignored by Git. Configure backend addresses in the sketches for your network.

## Local data

.env, SQLite databases, credentials, logs, virtual environments, and generated plant caches are excluded from version control. Database tables are created when the backend starts.

The frontend is maintained in a separate local project and is not included in this backend repository.
