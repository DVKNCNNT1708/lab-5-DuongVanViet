# Readiness Checklist - Lab 05

Danh sach nay dung de kiem tra stack Docker Compose truoc khi nop bai.

- [x] **Database ready:** `db` dung PostgreSQL 15, co healthcheck `pg_isready`, co volume `db-data`, va map port `5432`.
- [x] **AI service ready:** `ai-service` tu build Dockerfile rieng, chay non-root, co `/health`, `/predict`, healthcheck va map port `9000`.
- [x] **API ready:** `api` chay non-root, giu healthcheck `/health`, doi DB va AI healthy bang `depends_on`, luu readings vao PostgreSQL va goi AI qua `http://ai-service:9000`.
- [x] **Environment variables:** `.env.example` co `APP_PORT`, `AI_PORT`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `SERVICE_VERSION`, `AUTH_TOKEN`, `DATABASE_URL`, `AI_SERVICE_URL`; khong commit secret that.
- [x] **Network & ports:** cac service giao tiep noi bo qua `team-internal`; API tham gia them `class-net`; ports 8000, 9000 va 5432 duoc map ra host de test.
- [x] **Version/tag:** version runtime dat theo quy uoc `v0.1.0-team-iot`. Khi nop that, build va push image len registry voi tag tuong ung.
- [x] **Newman evidence:** `postman/collections/FIT4110_lab05_iot.postman_collection.json` va environment local da san sang; `npm run test:compose` xuat report vao `reports/`.

Ghi chu:

```text
- Stack duoc cau hinh de chay duoc tu clone moi bang .env.example.
- Neu co .env rieng, Docker Compose van dung gia tri trong .env cho bien interpolation.
```
