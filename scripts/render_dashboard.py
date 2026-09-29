from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from statistics import mean
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOG_PATH = REPO_ROOT / "data" / "logs.jsonl"
DEFAULT_CONFIG_PATH = REPO_ROOT / "config" / "dashboard.yaml"
DEFAULT_OUTPUT_PATH = REPO_ROOT / "submission" / "evidence" / "11-dashboard-overview.svg"


def percentile(values: list[float], percent: int) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, round(percent / 100 * len(ordered) + 0.5) - 1))
    return ordered[index]


def load_records(path: Path, window_minutes: int) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
            timestamp = datetime.fromisoformat(record["ts"].replace("Z", "+00:00"))
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            continue
        record["_timestamp"] = timestamp
        records.append(record)

    if not records:
        return []
    end = max(datetime.now(timezone.utc), max(r["_timestamp"] for r in records))
    start = end - timedelta(minutes=window_minutes)
    return [record for record in records if record["_timestamp"] >= start]


def summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    requests = [r for r in records if r.get("event") == "request_received"]
    responses = [r for r in records if r.get("event") == "response_sent"]
    failures = [r for r in records if r.get("event") == "request_failed"]
    latencies = [float(r["latency_ms"]) for r in responses if isinstance(r.get("latency_ms"), (int, float))]
    ttfts = [float(r["ttft_ms"]) for r in responses if isinstance(r.get("ttft_ms"), (int, float))]
    tool_results = [r for r in records if isinstance(r.get("tool_success"), bool)]
    quality = [float(r["quality_score"]) for r in responses if isinstance(r.get("quality_score"), (int, float))]
    minute_counts: dict[str, int] = defaultdict(int)
    for record in requests:
        minute_counts[record["_timestamp"].strftime("%H:%M")] += 1

    return {
        "latency_p50": percentile(latencies, 50),
        "latency_p95": percentile(latencies, 95),
        "latency_p99": percentile(latencies, 99),
        "ttft_p95": percentile(ttfts, 95),
        "requests": len(requests),
        "peak_rpm": max(minute_counts.values(), default=0),
        "error_rate": len(failures) / len(requests) * 100 if requests else 0.0,
        "error_breakdown": dict(Counter(r.get("error_type", "unknown") for r in failures)),
        "retrieval_success": sum(r["tool_success"] for r in tool_results) / len(tool_results) * 100 if tool_results else 0.0,
        "cost_total": sum(float(r.get("cost_usd", 0)) for r in responses),
        "tokens_in": sum(int(r.get("tokens_in", 0)) for r in responses),
        "tokens_out": sum(int(r.get("tokens_out", 0)) for r in responses),
        "quality_avg": mean(quality) if quality else 0.0,
    }


def render_svg(config: dict[str, Any], stats: dict[str, Any], record_count: int) -> str:
    dashboard = config["dashboard"]
    values = {
        "latency": [f"P50 {stats['latency_p50']:.0f} ms", f"P95 {stats['latency_p95']:.0f} ms", f"P99 {stats['latency_p99']:.0f} ms", f"TTFT P95 {stats['ttft_p95']:.0f} ms"],
        "traffic": [f"{stats['requests']} requests", f"Peak {stats['peak_rpm']} requests/min"],
        "errors": [f"Error rate {stats['error_rate']:.2f}%", f"Retrieval success {stats['retrieval_success']:.1f}%", f"Breakdown {stats['error_breakdown'] or '{}'}"],
        "cost": [f"Total ${stats['cost_total']:.6f}", "Aggregated over selected window"],
        "tokens": [f"Input {stats['tokens_in']:,}", f"Output {stats['tokens_out']:,}", f"Total {stats['tokens_in'] + stats['tokens_out']:,}"],
        "quality": [f"Average {stats['quality_avg']:.3f}", "Heuristic score (0–1)"],
    }
    width, height = 1440, 900
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#08111f"/>',
        '<style>text{font-family:Arial,sans-serif}.title{font-size:28px;font-weight:700;fill:#f8fafc}.sub{font-size:14px;fill:#94a3b8}.panel{fill:#111d2f;stroke:#26364f;stroke-width:2}.pt{font-size:20px;font-weight:700;fill:#e2e8f0}.value{font-size:18px;fill:#67e8f9}.meta{font-size:13px;fill:#94a3b8}.ok{fill:#22c55e}.bad{fill:#ef4444}.line{stroke:#334155;stroke-width:1}</style>',
        f'<text x="48" y="52" class="title">{escape(dashboard["title"])}</text>',
        f'<text x="48" y="80" class="sub">Runtime source: data/logs.jsonl · Last {dashboard["time_range_minutes"]} minutes · Refresh {dashboard["refresh_seconds"]}s · {record_count} records</text>',
    ]
    card_width, card_height = 430, 330
    threshold_values = {
        "latency": stats["latency_p95"],
        "traffic": stats["peak_rpm"],
        "errors": stats["error_rate"],
        "cost": stats["cost_total"],
        "tokens": stats["tokens_in"] + stats["tokens_out"],
        "quality": stats["quality_avg"],
    }
    for index, panel in enumerate(dashboard["panels"]):
        col, row = index % 3, index // 3
        x, y = 48 + col * 466, 112 + row * 365
        threshold = panel["threshold"]
        actual = threshold_values[panel["id"]]
        threshold_passed = (
            actual <= threshold["value"]
            if threshold["operator"] == "lte"
            else actual >= threshold["value"]
        )
        status_class = "ok" if threshold_passed else "bad"
        status_text = "OK" if threshold_passed else "SLO BREACH"
        parts.extend([
            f'<rect x="{x}" y="{y}" width="{card_width}" height="{card_height}" rx="14" class="panel"/>',
            f'<text x="{x + 24}" y="{y + 38}" class="pt">{escape(panel["title"])}</text>',
            f'<text x="{x + 24}" y="{y + 64}" class="meta">Unit: {escape(str(panel["unit"]))}</text>',
            f'<line x1="{x + 24}" y1="{y + 80}" x2="{x + card_width - 24}" y2="{y + 80}" class="line"/>',
        ])
        for line_index, line in enumerate(values[panel["id"]]):
            parts.append(f'<text x="{x + 24}" y="{y + 120 + line_index * 34}" class="value">{escape(line)}</text>')
        threshold_text = f"SLO line: {threshold['aggregation']} {threshold['operator']} {threshold['value']} {panel['unit']}"
        parts.extend([
            f'<rect x="{x + 24}" y="{y + 270}" width="10" height="10" rx="5" class="{status_class}"/>',
            f'<text x="{x + 44}" y="{y + 280}" class="meta">{escape(status_text + " · " + threshold_text)}</text>',
            f'<text x="{x + 24}" y="{y + 310}" class="meta">Events: {escape(", ".join(panel["events"]))}</text>',
        ])
    parts.append('</svg>')
    return "\n".join(parts)


def serve_dashboard(
    *, log_path: Path, config: dict[str, Any], host: str, port: int
) -> None:
    window = int(config["dashboard"]["time_range_minutes"])
    refresh = int(config["dashboard"]["refresh_seconds"])

    class DashboardHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
            records = load_records(log_path, window)
            svg = render_svg(config, summarize(records), len(records))
            page = (
                "<!doctype html><html><head>"
                f'<meta http-equiv="refresh" content="{refresh}">'
                '<meta name="viewport" content="width=device-width,initial-scale=1">'
                '<title>LLMOps Dashboard</title></head>'
                f'<body style="margin:0;background:#08111f">{svg}</body></html>'
            ).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(page)))
            self.end_headers()
            self.wfile.write(page)

        def log_message(self, format: str, *args: Any) -> None:
            return None

    print(f"Dashboard: http://{host}:{port} (refresh {refresh}s)")
    server = ThreadingHTTPServer((host, port), DashboardHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Dashboard stopped.")
    finally:
        server.server_close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Render the six-panel LLMOps dashboard from JSONL logs")
    parser.add_argument("--logs", type=Path, default=DEFAULT_LOG_PATH)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--serve", action="store_true", help="Serve a live auto-refreshing dashboard")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8501)
    args = parser.parse_args()

    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    if args.serve:
        serve_dashboard(log_path=args.logs, config=config, host=args.host, port=args.port)
        return 0
    window = int(config["dashboard"]["time_range_minutes"])
    records = load_records(args.logs, window)
    if not records:
        raise SystemExit(f"No valid log records in the last {window} minutes: {args.logs}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render_svg(config, summarize(records), len(records)), encoding="utf-8")
    print(f"Rendered {len(records)} records to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
