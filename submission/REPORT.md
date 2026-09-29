# Báo cáo cá nhân — K4-L3A Day 13 Monitoring & LLMOps

> Mỗi học viên hoàn thiện một file duy nhất này. Khi dẫn evidence, dùng đường dẫn tương đối, ví dụ `evidence/07-trace-waterfall.png`.

## 1. Thông tin học viên

- **Họ và tên:** Bùi Đình Đề
- **MSSV:** 2A202602818
- **Lớp:** K4-L3A
- **Repository URL:** https://github.com/buide03/K4-L3A-Day13-BuiDinhDe-2A202602818-Monitoring-LLMOps
- **Commit SHA cuối:** Chưa tạo — điền sau khi chốt commit nộp bài
- **Challenge ID:** `day13-k4-l3a-monitoring-llmops-v1`
- **Tên project Langfuse cá nhân:** `day13-k4-l3a-2A202602818`

## 2. Evidence index

Điền đúng đường dẫn tới evidence thực tế. Có thể đổi tên hoặc dùng nhiều ảnh nếu cần.

| Evidence | Đường dẫn |
|---|---|
| Pytest cuối | [PNG](evidence/01-pytest.png), [output](evidence/01-pytest.txt) |
| Log validator | [PNG](evidence/02-log-validator.png), [output](evidence/02-log-validator.txt) |
| Dashboard validator | [PNG](evidence/03-dashboard-validator.png), [output](evidence/03-dashboard-validator.txt) |
| Structured log | [PNG](evidence/04-structured-log.png), [JSON](evidence/04-structured-log.json) |
| PII redaction | [PNG](evidence/05-pii-redaction.png), [output](evidence/05-pii-redaction.txt) |
| Correlation response headers | [output](evidence/cp1-response-headers.txt) |
| Trace list | [PNG](evidence/06-trace-list.png), [verification](evidence/06-trace-list.txt) |
| Trace waterfall | [PNG](evidence/07-trace-waterfall.png), [verification](evidence/07-trace-waterfall.txt) |
| Trace metadata | [PNG](evidence/08-trace-metadata.png), [verification](evidence/08-trace-metadata.txt) |
| Prompt versions | [PNG](evidence/09-prompt-versions.png), [verification](evidence/09-prompt-versions.txt) |
| Prompt promote/rollback | [promote v2](evidence/10a-prompt-promote-v2.png), [rollback v1](evidence/10b-prompt-rollback-v1.png), [verification](evidence/10-prompt-rollback.txt) |
| Prompt trace comparison | [output](evidence/cp2-prompt-trace-comparison.txt) |
| Dashboard runtime | [PNG](evidence/11-dashboard-overview.png), [snapshot](evidence/11-dashboard-overview.svg) |
| Incident metric | [PNG](evidence/12-incident-metric.png), [snapshot](evidence/12-incident-metric.svg), [window and values](evidence/12-incident-metric.txt) |
| Incident log | [PNG](evidence/13-incident-log.png), [JSON](evidence/13-incident-log.json) |
| Incident trace | [PNG](evidence/14-incident-trace.png), [verification](evidence/14-incident-trace.txt) |

### CP0 baseline evidence

| Evidence | Đường dẫn |
|---|---|
| API health | [output](evidence/cp0-health.txt) |
| Log validator baseline | [output](evidence/cp0-baseline-log-validator.txt) |
| Dashboard validator baseline | [output](evidence/cp0-baseline-dashboard-validator.txt) |
| Pytest baseline | [output](evidence/cp0-baseline-pytest.txt) |
| Langfuse trace verification | [output](evidence/cp0-langfuse-traces.txt) |

## 3. Kết quả kỹ thuật

| Nội dung | Baseline | Kết quả cuối | Nhận xét |
|---|---|---|---|
| `validate_logs.py` | 30/100 | 100/100 | Không thiếu schema/enrichment; 17 correlation IDs ở lần kiểm tra cuối; 0 PII leak. |
| `validate_dashboard.py` | 6/6 panel | 6/6 panel | Dashboard contract và runtime renderer đều dùng `data/logs.jsonl`. |
| `pytest` | 22 passed | 22 passed | Toàn bộ bộ test nguyên bản của bài lab đạt; thư mục `tests/` không thay đổi. |
| Số traces hợp lệ | 10 | ≥10 | Mỗi trace được kiểm chứng có root, retrieval và generation đúng quan hệ cha-con. |
| Số PII leak | 0 | 0 | Kiểm tra trên 23 log runtime CP1. |
| Latency P95 / TTFT P95 | 1651 ms / 50 ms | 2364 ms / 50 ms | Workload cuối gồm 10 request trong cửa sổ 60 phút; cold fetch làm tăng tail latency nhưng vẫn dưới SLO 3000 ms. |
| Retrieval success rate | 100% | 100% | 10/10 request CP2 retrieval thành công. |

## 4. Logging và PII

- **Cách tạo/nhận và truyền correlation ID:** Middleware xóa context khi bắt đầu request, dùng `x-request-id` do client cung cấp hoặc sinh `req-<8-hex>`, bind vào structlog và `request.state`, rồi trả cùng ID qua response header. Header `x-response-time-ms` ghi thời gian xử lý. Context được xóa trong `finally` để không rò sang request khác.
- **Các metadata được ghi vào structured log:** `ts`, `level`, `service`, `event`, `correlation_id`, `user_id_hash`, `session_id`, `feature`, `model`, `env`; response còn có latency, TTFT, token, cost, quality và trạng thái retrieval. `user_id` chỉ xuất hiện dưới dạng SHA-256 rút gọn.
- **Cách bảo đảm PII được scrub trước khi ghi:** Processor `scrub_event` duyệt đệ quy chuỗi trong dict/list/tuple và chạy trước `JsonlFileProcessor` cùng `JSONRenderer`. Các rule che email, điện thoại Việt Nam, CCCD và thẻ thanh toán.
- **Cách kiểm chứng kết quả:** Bộ test nguyên bản `python -m pytest -q` đạt 22 tests; `validate_logs.py` đạt 100/100 trên 23 records với 11 correlation IDs và 0 PII leak. Request runtime `req-c0ffee12` chứa đủ bốn loại PII giả nhưng log chỉ còn bốn marker `[REDACTED_*]`; response trả lại đúng correlation ID.

## 5. Tracing và prompt versioning

- **Cách xác nhận traces do chính tôi tạo trong project cá nhân:** Chạy workload từ repository cá nhân rồi dùng `scripts/verify_traces.py` truy vấn Langfuse Observations API v2. Kết quả xác nhận 10/10 trace khớp correlation ID trong log và không có PII nguyên văn trong observation I/O.
- **Cấu trúc root/retrieval/generation observations:** `lab-agent-run` loại `AGENT` là root; `retrieval` loại `RETRIEVER` và `generation` loại `GENERATION` đều có `parent_observation_id` bằng ID root. Generation ghi model, prompt link, input/output/total tokens, total cost và TTFT metadata; prompt/output được scrub trước khi capture.
- **Cách nối trace với log:** Dùng metadata `correlation_id`. Ví dụ `req-03669190` nối tới trace `69ca4d8466e1245d3c0e2c7a062bdaad`.
- **Prompt name:** `day13-chat`.
- **Version/label baseline:** v1 có `baseline` và hiện có `production` sau rollback.
- **Version/label candidate:** v2 có `candidate` và `latest`.
- **Trace ID của mỗi version:** baseline v1: `d8a0293383ead8edb4b3205bb5ee8a77`; candidate v2: `99865eacc7a55a1731ca11fd7b7a46f4`; production khi promote v2: `919aae3ebeed95ca11289af3d4e45d4a`.
- **Cách promote và rollback `production`:** Chuyển `production` sang v2, chạy request `req-f00d0002` để xác nhận trace version 2, sau đó gán lại `production` cho v1. Trạng thái cuối: v1=`baseline, production`; v2=`candidate, latest`.

## 6. Dashboard, SLO và alerts

- **Dashboard và sáu panel:** `scripts/render_dashboard.py --serve` cung cấp dashboard local tự refresh 30 giây, đọc log trong 60 phút và render sáu panel latency/TTFT, traffic, errors/retrieval, cost, tokens và quality với đơn vị cùng SLO line từ `config/dashboard.yaml`. Snapshot cuối: P95 2364 ms, TTFT P95 50 ms, 10 request, error 0%, retrieval 100%, cost $0.017679, 338 input/1111 output tokens và quality 0.88.
- **SLO và lý do chọn:** SLO `fast_successful_requests` yêu cầu 99.5% request trong 28 ngày có `response_sent` và latency không quá 3000 ms. Ngưỡng cao hơn baseline P95 để hấp thụ biến động fake LLM nhưng vẫn phát hiện tail latency ảnh hưởng người dùng.
- **Cách tính error budget:** `100% - 99.5% = 0.5%`; tương đương 5 bad events trên 1000 request hoặc `28 × 24 × 60 × 0.005 = 201.6` phút trong cửa sổ 28 ngày.
- **Ba alert và runbook tương ứng:** `high_user_latency` (P95 > 3000 ms trong 5m), `elevated_request_errors` (error rate > 2% trong 5m), và `degraded_answer_quality` (quality < 0.75 hoặc retrieval success < 90% trong 10m). Cả ba gửi `#day13-llm-alerts`, có severity/owner và runbook Metrics → Logs → Traces. Artifact: [SLO](../config/slo.yaml), [alert rules](../config/alert_rules.yaml), [runbook](../docs/alerts.md).

## 7. Điều tra challenge

- **Challenge ID:** `day13-k4-l3a-monitoring-llmops-v1`.
- **Khoảng thời gian điều tra:** `2026-09-29T10:42:21.711111Z` đến `2026-09-29T10:42:36.587631Z`.
- **Triệu chứng từ metrics:** Panel latency vượt SLO: P50 `2651 ms`, P95/P99 `3673 ms` so với threshold `3000 ms`; TTFT P95 vẫn `50 ms`, không có error và quality trung bình `0.84`. Client quan sát thời gian hoàn tất khoảng 12.2–14.9 giây khi concurrency 5.
- **Log line và correlation ID liên quan:** Sự kiện `response_sent` của `req-a1eeed22` có `latency_ms=3673`, `ttft_ms=50`, `feature=monitoring`, `tool_name=retrieval`, `tool_success=true`, model `claude-sonnet-4-5` và cost `$0.00165`.
- **Trace ID và span gây ảnh hưởng:** Trace `7a6817388098ee1b40ff3b9cc25bb85e`; root `lab-agent-run` mất `3.674 s`, child `retrieval` mất `2.501 s`, trong khi `generation` chỉ mất `0.151 s`. Cả ba có status OK.
- **Root cause:** Challenge bật `rag_slow`, chèn độ trễ 2.5 giây vào bước retrieval. Retrieval đồng bộ dùng `time.sleep`, vì vậy nó vừa chiếm phần lớn thời gian của trace vừa chặn event loop; ở concurrency 5, các request xếp hàng nên latency nhìn từ client tăng tới 12–15 giây. Generation, TTFT, cost và error rate không cho thấy bất thường tương ứng.
- **Fix action:** Đã tắt incident sau khi thu thập evidence. Với hệ thống thật, rollback dependency/config retrieval gây chậm, áp timeout và fallback sang cached/general context; không retry không giới hạn. Chuyển retrieval blocking sang async I/O hoặc chạy trong worker/thread để không khóa event loop.
- **Preventive measure:** Theo dõi riêng retrieval P95 và tỷ lệ timeout, thêm timeout/circuit breaker/cache, cảnh báo khi retrieval chiếm phần lớn root latency, và chạy load test concurrency trong CI/staging trước khi phát hành thay đổi retrieval.

## 8. Giải thích và tự đánh giá

- **Một quyết định kỹ thuật quan trọng và lý do:** Tôi đặt processor scrub PII đệ quy trước cả file writer và JSON renderer. Nhờ đó cùng một chính sách bảo vệ được chuỗi ở mọi độ sâu trong payload và dữ liệu nhạy cảm không thể đi tới bất kỳ sink nào ở dạng nguyên văn.
- **Một lỗi/blocker đã gặp:** Sau khi sửa logging, validator vẫn có thể đọc các record cũ không đúng schema trong `data/logs.jsonl`; ngoài ra prompt metadata từng có nguy cơ rơi về `local-fallback` khi cấu hình Langfuse chưa sẵn sàng.
- **Cách tìm nguyên nhân và xử lý:** Tôi đối chiếu từng record theo timestamp/correlation ID, lưu baseline, làm sạch log trước workload mới và khởi động lại API. Với prompt, tôi kiểm tra key/base URL, `prompt_source`, name/label và xác nhận lại bằng trace của cả v1 lẫn v2.
- **Cách hiểu luồng Metrics → Logs → Traces:** Metrics chỉ ra cửa sổ P95 3673 ms vượt SLO. Trong cửa sổ đó, log `req-a1eeed22` ghi latency 3673 ms. Correlation ID dẫn tới trace `7a6817388098ee1b40ff3b9cc25bb85e`, nơi retrieval mất 2.501 s còn generation chỉ 0.151 s; vì vậy nguyên nhân nằm ở retrieval blocking chứ không phải LLM.
- **Vai trò của prompt version, token/cost, SLO hoặc rollback trong vận hành LLM:** Version và label cho phép thử v2, quan sát chất lượng/latency/token/cost rồi promote mà không sửa code; khi có rủi ro có thể chuyển `production` về v1 ngay. Token/cost giúp kiểm soát ngân sách, còn SLO và error budget biến trải nghiệm người dùng thành ngưỡng vận hành và cảnh báo đo được.
- **Điều quan trọng nhất đã học:** Observability chỉ hữu ích khi metric, structured log và trace dùng cùng metadata liên kết, đồng thời telemetry cũng phải được xem như dữ liệu nhạy cảm cần scrub trước khi lưu hoặc gửi ra ngoài.
- **Hạn chế hoặc phần chưa hoàn thành, nếu có:** Fake LLM/RAG và dashboard local phù hợp phạm vi lab nhưng chưa thay thế backend metrics, alert delivery và load profile production; ba alert hiện là contract/runbook, chưa kết nối Slack thật.

## 9. Checklist trước khi nộp

- [ ] Kết quả và evidence thuộc commit SHA cuối.
- [x] Tất cả ảnh/output mở được bằng đường dẫn tương đối.
- [x] Incident evidence nối đúng metric → log → trace.
- [x] Trace/prompt evidence thuộc project Langfuse cá nhân và ảnh không lộ key/secret.
- [x] Repository chạy lại được theo README.
- [x] Không có secret, API key, PII thô hoặc evidence của người khác/lớp khác.
- [ ] URL repo và commit SHA cuối đã được nộp trên LMS/Codelabs.
