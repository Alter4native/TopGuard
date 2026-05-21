# Deployment

## 1. MVP target

Первый deployment: локальный Docker Compose на одном компьютере/сервере.

Сервисы:
- `ai-service`
- `backend`
- `frontend`
- `postgres`
- `redis`
- `qdrant`
- `nginx`

## 2. Local defaults

- Одна камера.
- Default source для локальной разработки: USB/webcam.
- RTSP включается через настройку `source_type=rtsp` и `source_uri`.
- CPU inference baseline.
- GPU optimization добавляется после MVP через ONNX Runtime GPU/TensorRT/OpenVINO.

## 3. Volumes

Постоянные данные:
- PostgreSQL data;
- Qdrant data;
- snapshots;
- uploaded person photos;
- model weights.

Планируемые volume paths:

```text
storage/postgres
storage/qdrant
storage/snapshots
storage/person-photos
ai-service/models
```

## 4. Network boundaries

Public через nginx:
- `/` -> frontend
- `/api/*` -> backend public API

Internal:
- `ai-service -> backend /internal/*`
- `backend -> postgres`
- `backend -> redis`
- `backend/ai-service -> qdrant`

`/internal/*` не публикуется наружу.

## 5. Environment variables

Обязательные группы:
- database URL;
- Redis URL;
- Qdrant URL;
- JWT secret;
- service token;
- snapshot storage path;
- model path;
- camera source defaults;
- retention days.

Реальные секреты не хранятся в git. В репозиторий добавляется только `.env.example`.

## 6. Healthchecks

Backend:
- `/api/health`
- проверка postgres/redis/qdrant.

AI service:
- `/ai/health`
- проверка model loaded, camera manager state.

Frontend:
- nginx static health.

## 7. URLs

Локальный запуск через Compose nginx:
- frontend: `http://localhost:8080`
- backend API через nginx: `http://localhost:8080/api`
- ai-service health через nginx: `http://localhost:8080/ai/health`

Локальный dev запуск:
- backend direct: `http://localhost:8000/api/health`
- ai-service direct: `http://localhost:8010/ai/health`
- ai-service camera status: `http://localhost:8010/ai/camera/status`
- ai-service detector status: `http://localhost:8010/ai/detector/status`
- ai-service tracker status: `http://localhost:8010/ai/tracker/status`
- ai-service events status: `http://localhost:8010/ai/events/status`
- frontend Vite: `http://localhost:5173`

## 8. Camera credentials

RTSP credentials must be stored only in a local `.env` file and must not be committed.

Example format:

```text
CAMERA_SOURCE_TYPE=rtsp
CAMERA_SOURCE_URI=rtsp://username:password@camera-ip:554/path
```

The exact RTSP path depends on the camera vendor/model.

Event-related env:

```text
EVENT_COOLDOWN_SECONDS=60
KNOWN_PERSON_EVENT_COOLDOWN_SECONDS=120
UNKNOWN_PERSON_EVENT_COOLDOWN_SECONDS=120
RESTRICTED_ZONE_EVENT_COOLDOWN_SECONDS=300
CAMERA_OFFLINE_EVENT_COOLDOWN_SECONDS=300
PEOPLE_COUNT_INTERVAL_SECONDS=10
```

Recognition-related env:

```text
FACE_RECOGNITION_RUNTIME=simple
FACE_EMBEDDING_DIM=32
FACE_EMBEDDING_MODEL_NAME=simple-hash-face-embedding
FACE_RECOGNITION_THRESHOLD=0.65
EMBEDDING_STORE_RUNTIME=qdrant
QDRANT_URL=http://qdrant:6333
QDRANT_COLLECTION_PERSON_FACE_EMBEDDINGS=person_face_embeddings
QDRANT_TIMEOUT_SECONDS=3
```

The `simple` runtime is for MVP wiring and tests, not production biometrics. `EMBEDDING_STORE_RUNTIME=memory` is acceptable for isolated local tests; Compose should use `qdrant`.

Vector DB checks:

```powershell
docker compose -f .\infra\docker-compose.yml up -d qdrant
Invoke-RestMethod http://localhost:8010/ai/vector/status
```

Backend dev users:

```text
admin / admin
operator / operator
viewer / viewer
```

These are local in-memory users for MVP development. They must not be used as production credentials.

Frontend local dashboard:

```powershell
cd .\frontend
npm install
npm run build
npm run dev
```

Local URLs:

```text
Frontend: http://localhost:5173
Backend API through Vite proxy: http://localhost:5173/api
AI service through Vite proxy: http://localhost:5173/ai
```

For a complete local dashboard smoke test, run backend on `8000`, AI-service on `8010`, then open `http://localhost:5173` and sign in with a local dev user.

Database migration command:

```powershell
cd .\backend
..\.venv\Scripts\alembic -c .\database\alembic.ini upgrade head
```

## 9. Этап 1 - deployment decisions

- Docker Compose является единственным обязательным deployment для MVP.
- Kubernetes остается production roadmap.
- Локальный запуск должен работать без GPU.
- Snapshot storage закрыт и не мапится как public static directory.
