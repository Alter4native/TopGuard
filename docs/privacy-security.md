# Privacy and Security

## 1. MVP policy

Система работает с персональными и биометрическими данными. Минимальный baseline:

- хранить только нужные данные;
- не публиковать snapshots напрямую;
- не логировать embeddings, tokens, passwords, raw face crops;
- ограничивать доступ через JWT и RBAC;
- удалять события и snapshots старше 30 дней;
- хранить secrets только в `.env`, не в git.
- хранить RTSP credentials только в локальном `.env`, не в документации и не в commits.

## 2. Доступ к данным

### Snapshots

- Хранятся в private storage.
- В БД хранится storage key.
- `snapshot_url` на уровне event payload означает private storage key, а не публичную ссылку.
- Доступ только через backend endpoint после проверки auth/RBAC.
- Роли `admin`, `operator`, `viewer` могут смотреть snapshots, если имеют доступ к событию.

### Фото известных людей

- Загружаются только через backend.
- Доступны только `admin` и `operator`.
- `viewer` не управляет людьми и не загружает фото.

### Face embeddings

- Разрешено хранить embeddings известных людей в Qdrant.
- Embeddings не пишутся в application logs.
- Payload в Qdrant содержит только технические ссылки: `person_id`, `photo_id`, `embedding_model`, `created_at`.
- Stage 9 API stores embedding metadata only and does not return raw vectors.

## 3. RBAC

`admin`:
- управление пользователями, камерами, людьми, настройками, retention;
- просмотр всех событий и snapshots.

`operator`:
- просмотр камер, статусов, событий и snapshots;
- управление известными людьми;
- загрузка фото;
- изменение thresholds/restricted zones, если включено в настройках.

`viewer`:
- только просмотр камер, статусов, событий и snapshots;
- без доступа к людям, фото, моделям и настройкам.

## 4. API protection

Public API:
- JWT access token;
- refresh token rotation;
- rate limit через Redis;
- audit log для write operations.

Stage 7 status:
- JWT и RBAC реализованы на API уровне.
- Dev users are in-memory only: `admin`, `operator`, `viewer`.
- PostgreSQL schema for users/roles/audit logs is implemented in Stage 8.
- Route-level persistence switch, refresh token persistence and audit log middleware are scheduled for later backend/security steps.

Internal API:
- service token для `ai-service -> backend`;
- недоступен через публичный nginx route;
- payload validation через Pydantic schemas.

## 5. Retention

Default retention: 30 дней.

Удаляются:
- старые events;
- связанные snapshot files;
- устаревшие audit/system records согласно отдельной политике.

Не удаляются автоматически:
- users;
- persons;
- active embeddings;
- model registry.

## 6. Logging

Разрешено логировать:
- camera_id;
- event_id;
- latency;
- FPS;
- counts;
- error codes.

Запрещено логировать:
- passwords;
- JWT/refresh tokens;
- service tokens;
- RTSP camera login/password;
- face embeddings;
- raw images as base64;
- private snapshot paths в публичных ошибках.

## 7. Threat model MVP

Основные риски:
- неавторизованный доступ к snapshots;
- утечка embeddings или фото известных людей;
- viewer получает write access;
- event storm создает отказ в обслуживании;
- открытый internal API;
- secrets попадают в git.

Контрмеры:
- private storage;
- RBAC на каждом endpoint;
- service token для internal API;
- rate limit;
- retention job;
- `.env.example` без реальных секретов;
- audit logging.

## 8. Этап 1 - security decisions

- Snapshot URL не должен быть публичным.
- Face embeddings можно хранить в vector DB.
- Фото людей доступны только `admin`/`operator`.
- Retention MVP: 30 дней.
- Событие `people_count` не должно сохранять лишние персональные данные.

## 9. Этап 10 - vector storage privacy boundary

- Raw face vectors не возвращаются через public API.
- Backend хранит и выдает только metadata профиля: `person_id`, `photo_id`, `embedding_model`, `embedding_dim`, `vector_collection`, threshold.
- Qdrant payload не должен содержать ФИО, логины, фото или camera credentials.
- Удаление embeddings по человеку доступно только `admin`/`operator`.
- Для production нужно включить backup/retention policy для Qdrant storage и audit log удаления embeddings.

## 10. Этап 11 - dashboard security boundary

- Dashboard хранит access/refresh token только в `sessionStorage` для local MVP, не в постоянном `localStorage`.
- `viewer` не получает UI controls для people management, uploads, camera mutation и settings mutation.
- Backend RBAC остается источником истины: скрытие controls на frontend не считается защитой само по себе.
- Snapshot не открывается как public URL; UI вызывает авторизованный endpoint и показывает private storage metadata.
- Фото известных людей доступны только через `admin`/`operator` routes.
