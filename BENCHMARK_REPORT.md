# Benchmark & Observability Report — Day 14

**Họ tên:** Lê Thanh Tùng  
**MSSV:** 2A202603819  
**Lớp:** K5-L3B  
**Ngày chạy:** 26/11/2026  
**Môi trường:** Apple M2, macOS 15, Docker Desktop (4 vCPU, 8GB RAM, Engine 29.1.3), Python 3.11.16  

---

## 1. SLO của agent

| SLI | SLO | Lý do chọn ngưỡng này |
|---|---|---|
| p95 latency `/ask` | < 500 ms | Đảm bảo 95% yêu cầu tương tác hội thoại với agent phản hồi trong nửa giây, mang lại trải nghiệm mượt mà cho người dùng. |
| Error rate `/ask` | < 2.0 % | Cho phép dung sai nhỏ đối với lỗi mạng hoặc rate limit tạm thời từ nhà cung cấp mô hình LLM thượng nguồn. |
| Accuracy trên golden dataset | ≥ 90.0 % | Đảm bảo chất lượng tri thức trả về chính xác, không bị ảo giác hoặc trả lời sai kiến thức hệ thống cốt lõi. |

---

## 2. Benchmark hiệu năng (develop, `load_test.py`)

### 2.1 Concurrency vs latency (agent v2)

Số liệu đo thực tế từ `reports/load_v2_c*.json`:

| Concurrency | RPS | p50 (ms) | p95 (ms) | p99 (ms) | Error rate | SLO |
|---|---|---|---|---|---|---|
| 1 | 4.00 | 189.9 | 231.2 | 1707.1 | 0.00% | ✅ PASS |
| 10 | 34.69 | 191.2 | 225.4 | 1693.6 | 0.50% | ✅ PASS |
| 50 | 132.50 | 195.9 | 247.0 | 1700.2 | 0.80% | ✅ PASS |
| 100 | 56.29 | 922.4 | 4883.0 | 5297.7 | 1.60% | ❌ FAIL (p95 > 500ms) |

**Nhận xét:** RPS có tăng tuyến tính theo concurrency không? Vì sao?  
- **Không.** RPS tăng mạnh từ concurrency 1 (4.0 RPS) lên 10 (34.69 RPS) và đạt đỉnh ở 50 (132.5 RPS). Tuy nhiên khi lên tới concurrency 100, RPS bị giảm mạnh xuống còn 56.29 RPS đồng thời độ trễ tăng vọt (p95 lên đến 4,883 ms).
- **Nguyên nhân:** Khi concurrency vượt quá khả năng xử lý đồng thời của event loop tiến trình đơn (single worker) và các giới hạn kết nối socket/CPU contention, hàng đợi (queueing delay) bắt đầu phình to, dẫn đến tắc nghẽn và latency tăng vọt.

### 2.2 Tail latency

Số liệu đo thực tế từ `reports/load_v2_slow_*.json`:

| `MOCK_SLOW_RATE` | avg (ms) | p95 (ms) | p99 (ms) |
|---|---|---|---|
| 0 | 191.2 | 217.2 | 222.1 |
| 0.03 (mặc định) | 223.4 | 225.7 | 1684.0 |
| 0.1 | 387.5 | 1696.1 | 1711.3 |

**Nhận xét:** Chỉ số nào nhạy nhất với request chậm? Vì sao SLO không nên đặt theo average?  
- **p99 và p95** là các chỉ số nhạy nhất với các request bị chậm bất thường. Ở mức `MOCK_SLOW_RATE=0.03`, trong khi avg chỉ tăng nhẹ từ 191.2 ms lên 223.4 ms (tưởng chừng bình thường), p99 đã nhảy vọt từ 222.1 ms lên 1684.0 ms. Khi tỷ lệ chậm tăng lên 0.1 (10%), p95 bị kéo lên 1696.1 ms.
- **Vì sao không nên dùng average cho SLO:** Giá trị trung bình (average/mean) bị che mờ bởi số đông request chạy nhanh, làm nhà quản trị hệ thống không nhìn thấy một bộ phận người dùng (3% đến 5%) đang phải chịu trải nghiệm cực kỳ tệ hại (chờ gần 2 giây).

---

## 3. Benchmark chất lượng (develop, `eval/run_eval.py`)

Số liệu đo thực tế từ `reports/eval_v1.json`, `reports/eval_v2.json`, và `reports/eval_v2_fixed.json`:

| Chỉ số | Agent v1 | Agent v2 | Agent v2 (sau khi sửa KB) |
|---|---|---|---|
| Accuracy | 4.3% (1/23) | 91.3% (21/23) | 100.0% (23/23) |
| Avg tokens / câu | 57.9 | 108.7 | 113.0 |
| Tổng cost (USD) | $0.000415 | $0.000756 | $0.000785 |
| Cost / câu đúng (USD) | $0.00041475 | $0.00003599 | $0.00003413 |
| Quality gate | ❌ FAIL | ✅ PASS | ✅ PASS |

**Những câu v2 trả lời sai ban đầu và cách bạn sửa:**

| ID | Keyword bị thiếu | Bạn đã sửa gì |
|---|---|---|
| `security-02` | `token`, `hết hạn`, `chữ ký` | Bổ sung tri thức vào `KNOWLEDGE_BASE` trong `mock_llm.py` định nghĩa JWT là token có hạn hết hạn và mang chữ ký số kiểm tra tính toàn vẹn. |
| `scaling-03` | `cpu`, `memory`, `custom metrics` | Bổ sung tri thức vào `KNOWLEDGE_BASE` định nghĩa Kubernetes HPA tự động scale dựa trên CPU, memory và custom metrics. |

**Nhận xét về trade-off chất lượng / chi phí / latency giữa v1 và v2:**  
- **Về chất lượng:** Agent v2 tích hợp Retrieval (RAG) nâng độ chính xác vượt bậc từ 4.3% lên 100%, giải quyết triệt để vấn đề ảo giác/trả lời chung chung của v1.
- **Về độ trễ:** Bước tìm kiếm tài liệu (retrieval) cộng thêm ~20–30 ms vào p95 (192.9 ms lên 222.0 ms), hoàn toàn nằm trong ngưỡng chấp nhận được của SLO (< 500 ms).
- **Về chi phí:** Dù chi phí tuyệt đối cho 23 câu tăng từ $0.000415 lên $0.000785 do prompt chứa thêm context, nhưng **chi phí trên mỗi câu trả lời đúng** giảm hơn 12 lần (từ $0.000415 xuống $0.000034), mang lại hiệu quả kinh tế cao hơn gấp nhiều lần.

---

## 4. Observability stack (production)

### 4.1 Screenshot

Các ảnh minh họa thực tế đã được chuẩn bị trong thư mục `screenshots/`:
- [x] Dashboard Grafana khi đang có tải (thấy rõ Golden Signals): [grafana-dashboard.png](screenshots/grafana-dashboard.png)
- [x] Một trace chậm trong Jaeger (thấy span nào chiếm thời gian): [jaeger-slow-trace.png](screenshots/jaeger-slow-trace.png)
- [x] Một trace lỗi trong Jaeger (có event `exception`): [jaeger-error-trace.png](screenshots/jaeger-error-trace.png)
- [x] Trang Alerts của Prometheus với ít nhất 1 alert đang **firing**: [prometheus-alert-firing.png](screenshots/prometheus-alert-firing.png)

### 4.2 Thí nghiệm "phá hệ thống"

| # | Thay đổi | Alert nào firing | Thời gian từ lúc đổi → firing | Panel nào phản ánh rõ nhất |
|---|---|---|---|---|
| A | `MOCK_ERROR_RATE=0.2` | `HighErrorRate` | ~15s (3 evaluation cycles 5s) | HTTP Error Rate (%) |
| B | `MOCK_SLOW_RATE=0.3` | `HighP95Latency` | ~30s (đạt ngưỡng p95 > 500ms liên tục) | Latency Percentiles (p95/p99) |
| C | `LLM_MODEL=mock-llm-large` | `HighTokenCostRate` / `HighP95Latency` | ~25s | Estimated Cost / min & Latency |
| D | `docker pause` 1 instance | `InstanceDown` | ~15s (Prometheus scrape fail 3 lần) | Healthy Instances Gauge (3 -> 2) |
| E | `AGENT_VERSION=v1` | *Không alert nào firing* | N/A | Quality Eval accuracy drop |

**Thí nghiệm E không làm alert nào firing. Bạn sẽ phát hiện loại sự cố này trong production bằng cách nào?**  
- Hệ thống observability hạ tầng (metrics kỹ thuật) chỉ thấy HTTP 200, latency thấp và không có exception nên không thể kích hoạt alert.
- **Cách phát hiện trong production:**
  1. **Continuous Evaluation / Synthetic Monitoring:** Thiết lập một cron job định kỳ chạy bộ eval (golden dataset) 10 phút/lần tới endpoint staging/production, nếu accuracy < 90% sẽ gửi alert tới PagerDuty/Slack.
  2. **LLM-as-a-judge & User Feedback Loop:** Thu thập tỷ lệ người dùng nhấn dislike / thumbs down hoặc rate câu trả lời rỗng/ngắn bất thường để kích hoạt cảnh báo suy thoái chất lượng (Quality Degradation Alert).

### 4.3 Debug bằng trace

Chọn 1 trace chậm nhất tìm được:

- `trace_id`: `7a8f3b2c1e4d9a01`
- Tổng thời gian: `1720.0 ms`
- Span chiếm nhiều thời gian nhất: `llm.mock_call` (`1695.0 ms`, chiếm `98.5%`)
- Dòng log tương ứng:

```json
{"ts": "2026-11-26T14:43:35.120Z", "level": "INFO", "event": "request_completed", "trace_id": "7a8f3b2c1e4d9a01", "route": "/ask", "status": 200, "duration_ms": 1720.0, "llm_duration_ms": 1695.0, "tokens": 112, "cost_usd": 0.000084}
```

---

## 5. Benchmark scaling (production, Locust headless, 30 users)

Số liệu đo thực tế từ `benchmark-results/scale_1_stats.csv` và `benchmark-results/scale_3_stats.csv`:

| Số instance | RPS | p50 (ms) | p95 (ms) | p99 (ms) | Failures |
|---|---|---|---|---|---|
| 1 | 16.17 | 200 | 490 | 1700 | 0 (0.0%) |
| 3 | 15.45 | 190 | 1700 | 1700 | 1 (0.4%) |

**Giải thích kết quả:** Scale có cải thiện p95 không? Nút thắt nằm ở đâu?  
- **Không cải thiện p95 đáng kể** đối với tail latency do mô hình LLM gây ra. 
- **Nút thắt nằm ở đâu:** Khi bottleneck chính nằm ở upstream dependency (độ trễ gọi LLM hoặc simulated tail latency 1500ms do `MOCK_SLOW_RATE`), việc nhân bản thêm instance tầng web application (CPU/RAM local) không giúp giảm thời gian chờ của cuộc gọi LLM phía sau. Muốn giải quyết triệt để cần áp dụng caching câu trả lời (Semantic Cache với Redis), timeout + retry thông minh, hoặc chuyển sang streaming response.

---

## 6. Kết luận

- **3 điều học được về benchmark & observability:**
  1. Đo lường hiệu năng AI Agent bắt buộc phải nhìn vào Percentiles (p95, p99) và Golden Signals thay vì chỉ nhìn vào trung bình hay uptime đơn thuần.
  2. Phải phân biệt rõ giữa Benchmark Kỹ thuật (Throughput, Latency, Error) và Benchmark Chất lượng (Accuracy, Token Cost, Hallucination) thông qua Golden Dataset.
  3. Distributed Tracing là chìa khóa then chốt để cô lập chính xác nút thắt cổ chai nằm ở bước RAG retrieval, LLM upstream hay application logic.
- **Nếu đưa agent này lên production thật, bạn sẽ thêm metric / alert nào nữa?**
  1. **Token Cost Budget Burn Rate Alert:** Cảnh báo khi tốc độ đốt tiền token trong 1 giờ vượt quá ngưỡng ngân sách dự kiến ngày.
  2. **Cache Hit Ratio Metric:** Đo lường tỷ lệ tận dụng Semantic Cache của các câu hỏi trùng lặp để giảm thiểu chi phí và hạ latency về dưới 50ms.
  3. **P95 TTFT (Time to First Token) Metric:** Đối với các agent hỗ trợ streaming, TTFT là chỉ số cảm nhận người dùng quan trọng nhất cần được đo lường chặt chẽ.
