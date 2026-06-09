# FIT4110 Lab 05 - Docker Compose Readiness

**Hoc phan:** FIT4110 - Dich vu ket noi va Cong nghe nen tang  
**Buoi 5:** Dieu phoi da dich vu voi Docker Compose, readiness va AI service  
**Vai tro nhom:** Provider - AI Vision Detection API

Repo nay dong goi bai lab theo huong Provider. He thong gom:

- `api`: Provider API cho AI Vision, expose cac endpoint `/health`, `/vision/detect`, `/vision/detections/{detectionId}`, `/vision/models/info`
- `ai-service`: backend mock mo phong model inference va endpoint `/predict`
- `db`: PostgreSQL de hoan chinh stack Compose readiness

Muc tieu cua repo la:

- khop contract OpenAPI da chot giua Provider va Consumer
- build va run duoc bang Docker Compose
- co healthcheck ro rang cho API, AI backend va DB
- chay Newman thanh cong trong stack Compose
- sinh report de nop va de GitHub Actions check

## Contract

Contract hien tai nam o [contracts/iot-ingestion.openapi.yaml](/d:/lab-5-duytienkaka/contracts/iot-ingestion.openapi.yaml).  
Mac du ten file duoc giu lai de tranh anh huong workflow co san, noi dung da duoc doi sang `AI Vision Detection API`.

Contract nay mo ta:

- `GET /health`
- `POST /vision/detect`
- `GET /vision/detections/{detectionId}`
- `GET /vision/models/info`

## Cau truc repo

```text
.
├── .github/workflows/lab05-check.yml
├── Dockerfile
├── Dockerfile.ai
├── docker-compose.yml
├── .env.example
├── RUN_COMPOSE.md
├── requirements.txt
├── contracts/
│   └── iot-ingestion.openapi.yaml
├── postman/
│   ├── collections/
│   │   └── FIT4110_lab05_iot_compose.postman_collection.json
│   └── environments/
│       └── FIT4110_lab05_local.postman_environment.json
├── checklists/
│   └── readiness-checklist.md
├── reports/
│   ├── newman-lab05-compose.html
│   └── newman-lab05-compose.xml
└── src/
    ├── ai_service/
    │   └── main.py
    └── iot_app/
        └── main.py
```

## Chay local khong dung Docker

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn iot_app.main:app --app-dir src --host 0.0.0.0 --port 8000
```

Kiem tra nhanh:

```bash
curl http://localhost:8000/health
```

## Chay bang Docker Compose

```bash
cp .env.example .env
docker compose up -d --build --wait
```

Stack se khoi dong theo thu tu:

- `db`
- `ai-service`
- `api`

Kiem tra health:

```bash
curl http://localhost:8000/health
curl http://localhost:9000/health
docker compose exec -T db pg_isready -U "$POSTGRES_USER"
```

Theo doi log:

```bash
docker compose logs -f
```

## Newman / Postman

Collection da duoc chuan bi san cho Provider AI Vision:

- [postman/collections/FIT4110_lab05_iot_compose.postman_collection.json](/d:/lab-5-duytienkaka/postman/collections/FIT4110_lab05_iot_compose.postman_collection.json)
- [postman/environments/FIT4110_lab05_local.postman_environment.json](/d:/lab-5-duytienkaka/postman/environments/FIT4110_lab05_local.postman_environment.json)

Chay test:

```bash
npm run test:compose
```

Collection se test:

- `GET /health`
- `POST /vision/detect`
- `GET /vision/detections/{detectionId}`
- `GET /vision/models/info`

Report sinh ra tai:

- [reports/newman-lab05-compose.xml](/d:/lab-5-duytienkaka/reports/newman-lab05-compose.xml)
- [reports/newman-lab05-compose.html](/d:/lab-5-duytienkaka/reports/newman-lab05-compose.html)

## Readiness checklist

Checklist nam o [checklists/readiness-checklist.md](/d:/lab-5-duytienkaka/checklists/readiness-checklist.md).

No xac nhan cac diem chinh:

- DB san sang
- AI backend san sang
- Provider API san sang
- bien moi truong dung
- network va ports dung
- contract va report day du

## Dieu kien de repo pass check

Workflow GitHub se kiem tra:

1. tao `.env` tu `.env.example`
2. `docker compose config --quiet`
3. `docker compose up -d --build --wait`
4. `GET http://localhost:8000/health`
5. `GET http://localhost:9000/health`
6. `docker compose exec -T db pg_isready -U "$POSTGRES_USER"`
7. `npm run test:compose`
8. checklist co it nhat 6 muc da tick

## Ghi chu cho Consumer

Neu nhom Consumer can import contract, hay dung chinh file OpenAPI trong `contracts/` de tranh lech schema, field name, status code, auth va example data.
