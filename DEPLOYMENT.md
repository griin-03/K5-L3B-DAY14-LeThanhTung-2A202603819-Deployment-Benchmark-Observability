# Deployment Information — Day 14 Lab

**Học viên:** Lê Thanh Tùng  
**Mã số sinh viên:** 2A202603819  
**Lớp:** K5-L3B  

---

## 1. Public URL
- **Production URL:** `https://k5-l3b-day14-lethanhtung-2a202603819.onrender.com`
- **Local Container Tested Port:** `http://localhost:8000`

---

## 2. Platform & Deployment Specs
- **Platform:** Render (Web Service Dockerfile native build, Region: Singapore)
- **Container Architecture:** Multi-stage `python:3.11-slim`, non-root user `appuser`

---

## 3. Test Commands & Verification

### 3.1. Liveness Probe (`GET /health`)
```bash
curl -i https://k5-l3b-day14-lethanhtung-2a202603819.onrender.com/health
```
**Actual Response:** `HTTP/2 200 OK`
```json
{
  "status": "ok"
}
```

### 3.2. Readiness Probe (`GET /ready`)
```bash
curl -i https://k5-l3b-day14-lethanhtung-2a202603819.onrender.com/ready
```
**Actual Response:** `HTTP/2 503 Service Unavailable` *(chưa gắn REDIS_URL)* hoặc `200 OK` *(khi có Redis)*:
```json
{
  "status": "not ready",
  "redis": false
}
```

### 3.3. Unauthenticated API Test (Missing Key)
```bash
curl -i -X POST https://k5-l3b-day14-lethanhtung-2a202603819.onrender.com/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Docker container là gì?"}'
```
**Actual Response:** `HTTP/2 401 Unauthorized`
```json
{
  "detail": "Missing or invalid API key. Include header: X-API-Key: <your-key>"
}
```

### 3.4. Authenticated API Test (Valid Key)
```bash
curl -i -X POST https://k5-l3b-day14-lethanhtung-2a202603819.onrender.com/ask \
  -H "X-API-Key: day14-secret-key" \
  -H "Content-Type: application/json" \
  -d '{"question": "Docker container là gì?"}'
```
**Actual Response:** `HTTP/2 200 OK`
```json
{
  "question": "Docker container là gì?",
  "answer": "Container là cách đóng gói app để chạy ở mọi nơi. Build once, run anywhere!"
}
```

### 3.5. Rate Limiting Test (Spam > 10 requests / min)
```bash
for i in {1..15}; do
  curl -s -o /dev/null -w "Request $i: HTTP %{http_code}\n" \
    -X POST https://day14-agent-production.up.railway.app/ask \
    -H "X-API-Key: day14-secret-key" \
    -H "Content-Type: application/json" \
    -d '{"question": "Test rate limit"}'
done
```
**Expected Result:** Request 1 đến 10 trả về `200`, từ request 11 trở đi trả về `429 Too Many Requests`.

---

## 4. Environment Variables
Các biến môi trường được inject tự động hoặc khai báo trong Dashboard:

| Variable | Description | Example / Production Value |
|---|---|---|
| `PORT` | Cổng HTTP lắng nghe (PaaS tự động cấp) | `8000` |
| `ENVIRONMENT` | Môi trường ứng dụng | `production` |
| `AGENT_API_KEY` | Khóa xác thực truy cập API | `day14-secret-key` |
| `REDIS_URL` | Đường dẫn kết nối Redis cluster/service | `redis://redis:6379/0` hoặc `redis://default:***@...railway.app:6379` |
| `RATE_LIMIT_PER_MINUTE` | Giới hạn số request/phút theo IP | `10` |
| `DAILY_BUDGET_USD` | Hạn mức chi phí token tối đa mỗi ngày | `10.0` |
| `LOG_LEVEL` | Cấp độ ghi log JSON | `INFO` |

---

## 5. Screenshots
- [Deployment Dashboard](screenshots/dashboard.png)
- [Service Running Status](screenshots/running.png)
- [API Test Results](screenshots/test.png)
