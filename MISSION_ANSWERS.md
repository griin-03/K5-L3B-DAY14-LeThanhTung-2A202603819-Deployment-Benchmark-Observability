# Day 14 Lab - Mission Answers

**Học viên:** Lê Thanh Tùng  
**Mã số sinh viên:** 2A202603819  
**Lớp:** K5-L3B  
**Repository:** https://github.com/griin-03/K5-L3B-DAY14-LeThanhTung-2A202603819-Deployment-Benchmark-Observability  

---

## Part 1: Localhost vs Production

### Exercise 1.1: Anti-patterns found trong `01-localhost-vs-production/develop/app.py`
1. **Hardcoded Secrets:** API key được gán cứng trực tiếp trong code (`api_key = "sk-dev-secret-key-12345"`). Nếu commit mã nguồn lên GitHub công khai sẽ làm lộ bí mật bảo mật.
2. **Hardcoded Configuration & Port:** Port chạy cứng `8000`, host `127.0.0.1` thay vì `0.0.0.0` và không đọc cấu hình từ biến môi trường (`os.getenv("PORT")`).
3. **Debug Mode bật cứng:** Bật `debug=True` hoặc log traceback chi tiết thẳng ra ngoài, gây nguy cơ rò rỉ cấu trúc hệ thống và dữ liệu nhạy cảm.
4. **Thiếu Health Check & Readiness Check:** Không có các endpoint `/health` và `/ready` để orchestration platform (Docker, K8s, Railway/Render) giám sát tình trạng sống/chết.
5. **Không có Graceful Shutdown:** Tắt tiến trình đột ngột, làm rớt các in-flight requests đang xử lý của người dùng.
6. **Sử dụng print() thay cho Structured Logging:** Ghi log không đồng nhất cấu trúc, không có timestamp chuẩn, không format JSON gây khó khăn khi thu thập log tập trung.

### Exercise 1.3: Comparison table

| Feature | Develop (`develop/app.py`) | Production (`production/app.py`) | Why Important? |
|---|---|---|---|
| **Config & Secrets** | Hardcoded trong source code (`sk-dev-...`) | Tập trung qua biến môi trường (`.env`, `os.getenv`) | Bảo vệ an toàn bí mật, tuân thủ 12-factor App, đổi config không cần sửa code. |
| **Port Binding** | Cố định `8000` | Đọc động từ biến môi trường `PORT` (do cloud platform cấp) | Các nền tảng PaaS (Railway, Render, Cloud Run) cấp port ngẫu nhiên. |
| **Health Check** | Không có endpoint kiểm tra | `GET /health` (liveness) và `GET /ready` (readiness) | Giúp container orchestrator biết khi nào cần restart hoặc ngưng điều hướng traffic. |
| **Shutdown** | Thoát đột ngột khi ngắt tiến trình | Graceful shutdown: chặn traffic mới, đợi hoàn tất in-flight requests | Tránh mất mát dữ liệu và lỗi 502/connection reset với người dùng. |
| **Logging** | Dùng hàm `print()` thô | Structured JSON logging có level, timestamp, context | Tương thích các hệ thống thu thập log (Datadog, Loki, CloudWatch, ELK). |
| **State Storage** | Lưu session trong bộ nhớ local (RAM) | Lưu tập trung trên Redis | Cho phép scale ngang nhiều instance mà không mất session người dùng. |

---

## Part 2: Docker Containerization

### Exercise 2.1: Dockerfile questions
1. **Base image:** Cần chọn base image tinh gọn và ổn định (ví dụ `python:3.11-slim`) để giảm thiểu các gói hệ thống không cần thiết, hạn chế lỗ hổng CVE và giảm thời gian pull/build.
2. **Working directory:** Sử dụng `WORKDIR /app` để quy hoạch tập trung mã nguồn, tránh ghi đè các file hệ thống ngoài thư mục gốc.
3. **Thứ tự layer và Docker cache:** Cần copy `requirements.txt` và chạy `pip install` trước khi `COPY . .` để tận dụng Docker cache layer khi mã nguồn thay đổi mà dependencies giữ nguyên.
4. **Non-root user:** Container không nên chạy dưới quyền `root`. Khởi tạo user riêng (vd: `appuser`) để giảm thiểu rủi ro leo thang đặc quyền khi bị tấn công.

### Exercise 2.3: Image size comparison
Thực nghiệm đo đạc thực tế từ quá trình build `my-agent:develop` và `my-agent:advanced`:

- **Single-stage (`my-agent:develop` / `python:3.11` full):** `1.67 GB`
- **Multi-stage (`my-agent:advanced` / `python:3.11-slim`):** `265 MB`
- **Chênh lệch giảm:** `~84.1%` dung lượng
- **Production check image (`06-lab-complete`):** `56 MB`

*Lý do giảm kích thước:* Multi-stage build tách biệt giai đoạn build (cần gcc, compiler, header files) và giai đoạn runtime chỉ chứa các thư viện Python đã cài đặt và mã nguồn ứng dụng trên nền `python:3.11-slim`.

---

## Part 3: Cloud Deployment

### Exercise 3.1: Railway / Render deployment
- **Live URL:** `https://k5-l3b-day14-lethanhtung-2a202603819.onrender.com`
- **Kết quả kiểm thử thực tế trên Cloud (Render):**
  1. `GET /health` ➜ `HTTP/2 200 OK`
     ```json
     {"status":"ok"}
     ```
  2. `POST /ask` (không có key) ➜ `HTTP/2 401 Unauthorized`
     ```json
     {"detail":"Missing or invalid API key. Include header: X-API-Key: <your-key>"}
     ```
  3. `POST /ask` (có header `X-API-Key: day14-secret-key`) ➜ `HTTP/2 200 OK`
     ```json
     {"question":"Docker container là gì?","answer":"Container là cách đóng gói app để chạy ở mọi nơi. Build once, run anywhere!"}
     ```
- **So sánh `railway.toml` vs `render.yaml`:**
  - `railway.toml`: File cấu hình nhẹ tập trung vào build pipeline (`[build] builder = "DOCKERFILE"`), khai báo đường dẫn kiểm tra sức khỏe `healthcheckPath = "/health"` và timeout. Railway tự động phát hiện port từ Dockerfile EXPOSE.
  - `render.yaml`: File dạng Infrastructure-as-Code (Blueprint) định nghĩa cụ thể tài nguyên theo cụm service (`type: web`, `env: docker`), cho phép khai báo chi tiết danh sách biến môi trường (`envVars`), thiết lập tự động sinh giá trị bí mật (`generateValue: true`) hoặc đồng bộ thủ công (`sync: false`) để bảo vệ an toàn secret.
- **Exercise 3.3 — Pipeline CI/CD Cloud Run:**
  - Qua `cloudbuild.yaml` và `service.yaml`: Pipeline gồm 3 bước chính:
    1. Build Docker image từ Dockerfile và gán tag theo commit SHA (`gcr.io/$PROJECT_ID/agent:$COMMIT_SHA`).
    2. Push container image đã build lên Google Artifact Registry / Container Registry.
    3. Triển khai image lên Cloud Run qua lệnh `gcloud run services replace service.yaml`, Cloud Run tự động cấp phát URL HTTPS và quản lý auto-scaling từ 0 đến N instance.

---

## Part 4: API Security

### Exercise 4.1-4.3: Test results

#### 1. Test API Key Authentication (`04-api-gateway/develop`)
- Lệnh gọi không có header `X-API-Key`:
```text
HTTP 401 Unauthorized
{"detail":"Missing API Key"}
```
- Lệnh gọi có header `X-API-Key: my-secret-key`:
```text
HTTP 200 OK
{"answer":"Mock LLM response for: hello","user_id":"anonymous"}
```

#### 2. Test JWT Authentication & Rate Limiting (`04-api-gateway/production`)
- Lấy token qua `POST /auth/token` với user `student` / `demo123`:
```text
HTTP 200 OK
{"access_token":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...","token_type":"bearer"}
```
- Gọi liên tiếp 15 requests bằng Bearer Token:
```text
Request  1: Mock LLM response for: what is docker? (200 OK)
Request  2: Mock LLM response for: what is docker? (200 OK)
...
Request 10: Mock LLM response for: what is docker? (200 OK)
Request 11: ❌ Rate limit exceeded (HTTP 429)
Request 12: ❌ Rate limit exceeded (HTTP 429)
```

### Exercise 4.4: Cost guard implementation
- Cơ chế bảo vệ chi phí token hoạt động bằng cách ghi nhận lượng token tiêu thụ sau mỗi lượt phản hồi của LLM.
- Mỗi request tính chi phí `cost_usd = (prompt_tokens * rate_input) + (completion_tokens * rate_output)`.
- Chi phí được tích lũy vào Redis theo key ngày: `cost:YYYY-MM-DD`. Khi tổng chi phí vượt ngưỡng trần cấu hình (`daily_budget_usd`), endpoint `/ask` trả mã lỗi `402 Payment Required` và ngừng chuyển tiếp request tới LLM, ngăn chặn rủi ro thâm hụt ngân sách tài khoản API.

---

## Part 5: Scaling & Reliability

### Exercise 5.1-5.5: Implementation notes

#### 1. Test Stateless Architecture với Redis (`05-scaling-reliability/production`)
Khởi động cụm 3 instance agent + Redis + Nginx Load Balancer:
```bash
docker compose -p k5-day14-scaling up -d --build --scale agent=3
python test_stateless.py
```
Output thực tế:
```text
Session test:
  Request 1: instance=agent-1, count=1
  Request 2: instance=agent-2, count=2
  Request 3: instance=agent-3, count=3
  Request 4: instance=agent-1, count=4
Session persistence verified across 3 agent instances via Redis!
```
*Nhận xét:* Dù Nginx round-robin điều hướng request tới các instance khác nhau, lịch sử hội thoại và bộ đếm phiên vẫn đồng nhất nhờ dữ liệu phiên được quản lý tập trung trên Redis.

---

## Part 6: Production Readiness Check Output

Output thực tế chạy từ script kiểm thử độc lập `check_production_ready.py` trong `06-lab-complete/`:

```text
================================================================
  Production Readiness Check — Day 14 Lab
================================================================

✅ 1. Dockerfile (multi-stage, < 500 MB)
     ✅ Dockerfile tồn tại
     ✅ requirements.txt tồn tại
     ✅ Multi-stage build (≥ 2 lệnh FROM)
     ✅ Base image gọn (slim / alpine / distroless) — stage cuối dùng python:3.11-slim
     ✅ Chạy bằng user non-root
     ✅ Có HEALTHCHECK
     ✅ Docker: build image thành công — 293s
     ✅ Docker: image < 500 MB — 56 MB
     ✅ Docker: container chạy được, GET /health → 200

✅ 2. docker-compose.yml (agent + redis)
     ✅ docker-compose.yml tồn tại
     ✅ Có service agent (build từ Dockerfile) + redis — services: agent, redis — đọc bằng docker compose config
     ✅ Service agent kết nối redis (REDIS_URL + depends_on)

✅ 3. .dockerignore
     ✅ .dockerignore tồn tại và có nội dung
     ✅ .dockerignore loại trừ .env (secrets)
     ✅ .dockerignore loại trừ __pycache__, venv

✅ 4. Health check endpoint (GET /health)
     ✅ Code có route /health
     ✅ Khi chạy: GET /health → 200 — uvicorn --workers 2

✅ 5. Readiness endpoint (GET /ready)
     ✅ Code có route /ready
     ✅ Khi chạy: GET /ready → 200
     ✅ Khi chạy: Redis mất kết nối → /ready 503 (còn /health vẫn 200)

✅ 6. API Key authentication
     ✅ Code đọc header X-API-Key
     ✅ Khi chạy: thiếu / sai API key → 401
     ✅ Khi chạy: API key đúng → 200

✅ 7. Rate limiting
     ✅ Code trả HTTP 429 khi vượt giới hạn
     ✅ Khi chạy: vượt giới hạn → 429 — 429 sau 5 request thành công (RATE_LIMIT_PER_MINUTE=5)
     ✅ Khi chạy: state nằm trong Redis — restart agent vẫn bị 429

✅ 8. Cost guard
     ✅ Code trả HTTP 402 khi hết budget
     ✅ Khi chạy: hết budget → 402 — 402 ở request thứ 1

✅ 9. Config từ environment variables
     ✅ app/config.py đọc biến môi trường
     ✅ .env.example liệt kê đủ biến cấu hình
     ✅ .env nằm trong .gitignore
     ✅ Không hard-code secret trong code
     ✅ Khi chạy: agent dùng AGENT_API_KEY và RATE_LIMIT_PER_MINUTE từ env

✅ 10. Structured logging
     ✅ Code ghi log dạng JSON
     ✅ Khi chạy: mọi dòng log của app là JSON hợp lệ — 7 dòng JSON

✅ 11. Graceful shutdown
     ✅ Code xử lý SIGTERM / lifespan shutdown
     ✅ Khi chạy: SIGTERM lúc đang có request → request vẫn 200, process tự thoát — exit code 0
     ✅ Docker: `docker stop` tắt êm (exit code 0, < 10s) — exit code 0, 0.5s

✅ 12. Public URL ready (Railway / Render config)
     ✅ Có railway.toml hoặc render.yaml (không chỉ toàn comment)
     ✅ railway.toml: builder + healthcheckPath = "/health"
     ✅ render.yaml: web service + healthCheckPath /health
     ✅ render.yaml: secret không ghi thẳng giá trị (generateValue / sync: false)
     ✅ App lắng nghe theo biến PORT do platform cấp

================================================================
  📋 Checklist Deliverable
     ✅ Dockerfile (multi-stage, < 500 MB)
     ✅ docker-compose.yml (agent + redis)
     ✅ .dockerignore
     ✅ Health check endpoint (GET /health)
     ✅ Readiness endpoint (GET /ready)
     ✅ API Key authentication
     ✅ Rate limiting
     ✅ Cost guard
     ✅ Config từ environment variables
     ✅ Structured logging
     ✅ Graceful shutdown
     ✅ Public URL ready (Railway / Render config)
----------------------------------------------------------------
  Result: 12/12 tiêu chí đạt · 43/43 checks passed
  🎉 PASS 12/12 — PRODUCTION READY! Deploy nào!
================================================================
```

---

## AI Log

1. **Prompt:** "Hỏi cách cấu hình sliding window rate limiting dùng Redis sorted set và xử lý TTL hiệu quả."
   - **Nhận được:** Gợi ý sử dụng `zremrangebyscore`, `zcard`, `zadd` và đặt `expire` 60s cho key của client.
   - **Tự sửa & kiểm tra:** Đã tích hợp hàm trong `06-lab-complete/app/rate_limiter.py`, bổ sung kiểm tra fallback nếu Redis gặp sự cố, test bằng script `check_production_ready.py` xác nhận đạt `PASS`.

2. **Prompt:** "Tối ưu Dockerfile cho ứng dụng FastAPI + Redis để image dưới 100MB và không chạy quyền root."
   - **Nhận được:** Gợi ý mô hình multi-stage build với `python:3.11-slim`, tạo `appuser` trong runtime stage.
   - **Tự sửa & kiểm tra:** Viết hoàn chỉnh `06-lab-complete/Dockerfile`, loại bỏ các gói build tool thừa ở runtime stage, kết quả image thực tế chỉ nặng 56 MB (vượt chuẩn < 500 MB).

3. **Prompt:** "Thiết kế Graceful shutdown cho FastAPI với Lifespan và ASGI Server uvicorn."
   - **Nhận được:** Cơ chế async context manager lifespan, kết hợp tracking in-flight requests và chuyển trạng thái `_is_ready = False`.
   - **Tự sửa & kiểm tra:** Cài đặt vào `app/main.py`, kiểm thử gửi SIGTERM khi request đang pending, kết quả request được hoàn tất trọn vẹn trước khi tiến trình tắt với exit code 0.
