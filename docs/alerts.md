# Alert Runbooks

All alerts are symptom-based and notify `#day13-llm-alerts`. Start with the affected time window, then follow **Metrics → Logs → Traces** using `correlation_id`. Do not include raw prompts, outputs, or PII in Slack.

## High user latency

- **Severity / duration:** warning for `latency_p95_ms > 3000` during 5 minutes.
- **SLI/SLO:** `fast_successful_requests`; 99.5% of requests should complete within 3000 ms over 28 days.
- **User impact:** answers arrive slowly or clients time out.
- **First checks:** (1) confirm P95/P99 and TTFT window; (2) find slow `response_sent` logs and correlation IDs; (3) compare retrieval and generation durations in Langfuse.
- **Mitigation:** reduce concurrency, disable the affected feature, or route to the stable prompt/model while isolating the slow dependency.
- **Owner:** `llm-platform`.

## Elevated request errors

- **Severity / duration:** critical for `error_rate_pct > 2` during 5 minutes.
- **SLI/SLO:** failed requests consume the 0.5% error budget.
- **User impact:** requests fail or return no answer.
- **First checks:** (1) confirm error rate and breakdown; (2) group `request_failed` logs by `error_type`; (3) inspect matching traces and the first failing child observation.
- **Mitigation:** disable the failing integration, retry only transient failures with limits, and roll back the latest risky configuration.
- **Owner:** `api-oncall`.

## Degraded answer quality

- **Severity / duration:** warning when average quality is below 0.75 or retrieval success is below 90% for 10 minutes.
- **SLI/SLO:** quality and retrieval guardrails in `config/slo.yaml`.
- **User impact:** answers may be incomplete, irrelevant, or unsupported by retrieved context.
- **First checks:** (1) compare quality and retrieval success; (2) filter affected features and correlation IDs; (3) inspect retrieval output, prompt version, token usage, and generation trace metadata.
- **Mitigation:** roll `production` back to the last stable prompt and temporarily disable the affected knowledge source or feature.
- **Owner:** `llm-quality`.
