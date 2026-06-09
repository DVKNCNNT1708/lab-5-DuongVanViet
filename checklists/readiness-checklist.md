# Readiness Checklist - Team Vision Lab 05

Danh sach nay dung de kiem tra stack Docker Compose truoc khi nop bai.

- [x] **Database ready:** `db` dung PostgreSQL 15, co healthcheck `pg_isready`, co volume `db-data`, va map port `5432`.
- [x] **AI service ready:** `ai-service` la mock YOLO-style inference worker, chay non-root, co `/health`, `/predict`, healthcheck va map port `9000`.
- [x] **API ready:** `api` expose contract Team Vision: `/health`, `/vision/detect`, `/vision/detections/{detectionId}`, `/vision/models/info`; API doi DB va AI healthy bang `depends_on`.
- [x] **Environment variables:** `.env.example` co `APP_PORT`, `AI_PORT`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `SERVICE_VERSION`, `MODEL_VERSION`, `AUTH_TOKEN`, `DATABASE_URL`, `AI_SERVICE_URL`; khong commit secret that.
- [x] **Network & ports:** cac service giao tiep noi bo qua `team-internal`; API tham gia them `class-net`; ports 8000, 9000 va 5432 duoc map ra host de test.
- [x] **Image tags:** image dung quy uoc `v0.1.0-team-vision`: `fit4110/ai-vision:v0.1.0-team-vision` va `fit4110/vision-inference:v0.1.0-team-vision`.
- [x] **Newman evidence:** `postman/collections/FIT4110_lab05_team_vision.postman_collection.json` va environment local da san sang; `npm run test:compose` xuat report vao `reports/`.

Ghi chu:

```text
- Stack duoc cau hinh de chay duoc tu clone moi bang .env.example.
- API luu detection vao PostgreSQL va goi AI worker noi bo bang hostname ai-service.
```
