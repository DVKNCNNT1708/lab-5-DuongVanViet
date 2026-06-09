# Readiness Checklist - Lab 05

Day la danh sach kiem tra de dam bao stack Docker Compose cua Provider AI Vision da san sang truoc khi gui bai.

- [x] **Database ready:** container DB da chay va phan hoi `pg_isready`.
- [x] **AI backend ready:** container backend mo phong model tra ve `200` cho `/health` va phan hoi `POST /predict`.
- [x] **Provider API ready:** API tra `200` cho `/health`, nhan `POST /vision/detect`, doc duoc `GET /vision/detections/{detectionId}` va `GET /vision/models/info`.
- [x] **Environment variables:** `.env.example` da co `AUTH_TOKEN`, `SERVICE_NAME`, `AI_SERVICE_URL`, `MODEL_NAME`, `MODEL_VERSION` va khong chua secret that.
- [x] **Network & Ports:** mang `team-internal` hoat dong, provider API map port `8000`, backend AI map port `9000`, DB su dung port `5432` trong stack.
- [x] **Contract & reports:** OpenAPI da duoc dat trong `contracts/`, Newman collection da khop contract va report duoc sinh trong `reports/`.

Ghi chu:

```text
- Stack da duoc canh theo contract AI Vision Detection API ma nhom Provider va Consumer da chot.
```
