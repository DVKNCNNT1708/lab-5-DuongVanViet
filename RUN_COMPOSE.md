# RUN_COMPOSE.md - Huong dan chay Lab 05

Tai lieu nay huong dan clone repo sach va chay lai toan bo stack Docker Compose cua Lab 05.

## 1. Chuan bi

Can co:

- Docker Desktop hoac Docker Engine co Compose v2.
- Node.js 20.x LTS neu muon chay Newman report.
- Git de clone repo.

## 2. Chay stack Docker Compose

Repo da co `.env.example` voi gia tri demo khong phai secret that. Neu muon tuy bien, tao file `.env` rieng:

```bash
cp .env.example .env
```

Build va chay 3 service:

```bash
docker compose up -d --build
```

Stack tao cac container:

- `fit4110-db-lab05`: PostgreSQL tren port 5432.
- `fit4110-ai-lab05`: AI mock service tren port 9000.
- `fit4110-api-lab05`: FastAPI IoT API tren port 8000.

Theo doi log:

```bash
docker compose logs -f
```

## 3. Kiem tra readiness

```bash
curl http://localhost:8000/health
curl http://localhost:9000/health
docker exec -it fit4110-db-lab05 pg_isready -U lab05 -d iotdb
```

Tao mot reading qua API:

```bash
curl -X POST http://localhost:8000/readings \
  -H "Authorization: Bearer local-dev-token" \
  -H "Content-Type: application/json" \
  -d '{"device_id":"ESP32-LAB-A01","metric":"temperature","value":31.5,"unit":"celsius","timestamp":"2026-05-13T08:30:00+07:00"}'
```

API se goi AI service qua hostname noi bo `ai-service` va luu reading vao PostgreSQL qua hostname `db`.

## 4. Chay Newman

Cai Node dependencies:

```bash
npm install
```

Chay test end-to-end tren stack Compose:

```bash
npm run test:compose
```

Report duoc xuat ra:

```text
reports/newman-lab05-compose.xml
reports/newman-lab05-compose.html
```

## 5. Dung stack

```bash
docker compose down
```

Neu can xoa luon volume PostgreSQL:

```bash
docker compose down -v
```

## 6. Lenh Makefile

```bash
make compose-up
make logs
make test-compose
make compose-down
```
