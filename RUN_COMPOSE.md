# RUN_COMPOSE.md - Huong dan chay Lab 05

Tai lieu nay huong dan clone repo sach va chay lai stack Docker Compose cua nhom Provider AI Vision.

## 1. Clone repo

```bash
git clone <repo-url>
cd FIT4110_lab05_docker_compose_readiness
```

## 2. Cai dependencies tuy chon

Can cai Node.js neu muon chay Newman:

```bash
npm install
```

## 3. Tao file env

```bash
cp .env.example .env
```

Mac dinh file `.env.example` da co san:

- `AUTH_TOKEN=local-dev-token`
- `SERVICE_NAME=ai-vision`
- `SERVICE_VERSION=1.0.0`
- `AI_SERVICE_URL=http://ai-service:9000`
- `MODEL_NAME=yolo-hospital-monitor`
- `MODEL_VERSION=yolov11n-hospital-2.3.1`

## 4. Build va chay stack

```bash
docker compose up -d --build --wait
```

Cac container duoc tao:

- `fit4110-db-lab05`
- `fit4110-ai-lab05`
- `fit4110-api-lab05`

## 5. Kiem tra health

```bash
curl http://localhost:8000/health
curl http://localhost:9000/health
docker compose exec -T db pg_isready -U "$POSTGRES_USER"
```

Kiem tra endpoint chinh cua Provider API:

```bash
curl -X POST http://localhost:8000/vision/detect \
  -H "Authorization: Bearer local-dev-token" \
  -H "Content-Type: application/json" \
  -d '{
    "requestId": "REQ-CAM-20260609-0001",
    "cameraId": "CAM-ER-01",
    "capturedAt": "2026-06-09T08:00:00Z",
    "traceId": "TRACE-20260609-0001",
    "zoneId": "ER-ENTRANCE",
    "motionLevel": 0.92,
    "notes": "Motion detected near emergency entrance",
    "imageSource": {
      "sourceType": "IMAGE_URL",
      "url": "https://media.hospital.local/camera/CAM-ER-01/frame-1001.jpg"
    }
  }'
```

Kiem tra backend AI mock:

```bash
curl -X POST http://localhost:9000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "requestId": "REQ-CAM-20260609-0001",
    "cameraId": "CAM-ER-01"
  }'
```

## 6. Chay Newman

```bash
npm run test:compose
```

Sau khi chay xong, report duoc sinh tai:

```text
reports/newman-lab05-compose.xml
reports/newman-lab05-compose.html
```

## 7. Theo doi log

```bash
docker compose logs -f
```

## 8. Dung stack

```bash
docker compose down
```

Neu muon xoa ca volume DB:

```bash
docker compose down -v
```

## 9. Meo go loi

- Dung `docker compose ps` de xem service da `healthy` hay chua.
- Neu API khong goi duoc backend AI, kiem tra `AI_SERVICE_URL=http://ai-service:9000`.
- Neu Newman fail do auth, kiem tra `authToken` trong Postman environment co trung voi `AUTH_TOKEN`.
- Neu DB fail readiness, kiem tra `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` trong `.env`.
