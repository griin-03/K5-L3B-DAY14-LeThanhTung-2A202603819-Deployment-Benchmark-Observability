# Deployment Information — Day 14 Lab

**Học viên:** Lê Thanh Tùng  
**Mã số sinh viên:** 2A202603819  
**Lớp:** K5-L3B  

---

## 1. Public URL
- **Production URL:** `https://day14-agent-production.up.railway.app` *(hoặc `https://day14-agent-production.onrender.com`)*
- **Local Container Tested Port:** `http://localhost:8000`

---

## 2. Platform & Deployment Specs
- **Platform:** Railway / Render (Web Service Dockerfile native build)
- **Container Architecture:** Multi-stage `python:3.11-slim`, non-root user `appuser`
- **Attached Addon:** Redis 7 Cloud Instance (Private Network URL)

---

## 3. Test Commands & Verification

### 3.1. Liveness Probe (`GET /health`)
```bash
curl -i https://day14-agent-production.up.railway.app/health
```
**Expected Response:** `HTTP/1.1 200 OK`
```json
{
  "status": "ok",
  "environment": "production"
}
```

### 3.2. Readiness Probe (`GET /ready`)
```bash
curl -i https://day14-agent-production.up.railway.app/ready
```
**Expected Response:** `HTTP/1.1 200 OK`
```json
{
  "status": "ready",
  "redis": "connected",
  "environment": "production"
}
```

### 3.3. Unauthenticated API Test (Missing Key)
```bash
curl -i -X POST https://day14-agent-production.up.railway.app/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Docker container là gì?"}'
```
**Expected Response:** `HTTP/1.1 401 Unauthorized`
```json
{
  "detail": "Missing X-API-Key header"
}
```

### 3.4. Authenticated API Test (Valid Key)
```bash
curl -i -X POST https://day14-agent-production.up.railway.app/ask \
  -H "X-API-Key: day14-secret-key" \
  -H "Content-Type: application/json" \
  -d '{"question": "Docker container là gì?"}'
```
**Expected Response:** `HTTP/1.1 200 OK`
```json
{
  "answer": "Mock LLM response for: Docker container là gì?",
  "model": "mock-llm-small",
  "usage": {
    "prompt_tokens": 12,
    "completion_tokens": 45,
    "total_tokens": 57,
    "cost_usd": 0.000085
  }
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
