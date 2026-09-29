from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langfuse import get_client

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.pii import PII_PATTERNS


def load_correlation_ids(path: Path) -> set[str]:
    correlation_ids: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            correlation_id = json.loads(line).get("correlation_id")
        except json.JSONDecodeError:
            continue
        if correlation_id:
            correlation_ids.add(correlation_id)
    return correlation_ids


def contains_raw_pii(value: Any) -> bool:
    serialized = json.dumps(value, ensure_ascii=False, default=str)
    return any(re.search(pattern, serialized) for pattern in PII_PATTERNS.values())


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify CP2 Langfuse trace structure")
    parser.add_argument("--logs", type=Path, default=REPO_ROOT / "data" / "logs.jsonl")
    parser.add_argument("--minutes", type=int, default=60)
    args = parser.parse_args()

    load_dotenv(REPO_ROOT / ".env")
    correlation_ids = load_correlation_ids(args.logs)
    now = datetime.now(timezone.utc)
    fields = "core,basic,time,io,metadata,model,usage,prompt,metrics,trace_context"
    observations = get_client().api.observations.get_many(
        fields=fields,
        expand_metadata=(
            "correlation_id,feature,prompt_name,prompt_label,prompt_version,"
            "prompt_source,cost_usd,ttft_ms"
        ),
        limit=1000,
        from_start_time=now - timedelta(minutes=args.minutes),
        to_start_time=now,
    ).data

    matched = [
        observation
        for observation in observations
        if isinstance(observation.metadata, dict)
        and observation.metadata.get("correlation_id") in correlation_ids
    ]
    by_trace: dict[str, list[Any]] = defaultdict(list)
    for observation in matched:
        by_trace[observation.trace_id].append(observation)

    valid_traces: list[tuple[str, str]] = []
    pii_hits = 0
    for trace_id, group in by_trace.items():
        roots = [item for item in group if item.name == "lab-agent-run"]
        retrievals = [item for item in group if item.name == "retrieval"]
        generations = [item for item in group if item.name == "generation"]
        if len(roots) != 1 or len(retrievals) != 1 or len(generations) != 1:
            continue
        root = roots[0]
        if any(item.parent_observation_id != root.id for item in retrievals + generations):
            continue
        correlation_id = str(root.metadata.get("correlation_id"))
        valid_traces.append((correlation_id, trace_id))
        pii_hits += sum(
            contains_raw_pii({"input": item.input, "output": item.output})
            for item in group
        )

    valid_traces.sort()
    print("CP2 Langfuse trace verification")
    print(f"Log correlation IDs: {len(correlation_ids)}")
    print(f"Valid root/retrieval/generation traces: {len(valid_traces)}")
    print(f"Raw PII matches in observation I/O: {pii_hits}")
    for correlation_id, trace_id in valid_traces:
        print(f"- {correlation_id} -> {trace_id}")

    if valid_traces:
        selected_trace_id = valid_traces[0][1]
        group = by_trace[selected_trace_id]
        root = next(item for item in group if item.name == "lab-agent-run")
        generation = next(item for item in group if item.name == "generation")
        print("\nSelected trace metadata")
        print(f"trace_id: {selected_trace_id}")
        print(f"user_id_hash: {root.user_id}")
        print(f"session_id: {root.session_id}")
        print(f"environment: {root.environment}")
        for key in ("correlation_id", "feature", "model", "prompt_name", "prompt_label", "prompt_version", "prompt_source"):
            print(f"{key}: {root.metadata.get(key)}")
        print(f"generation_model: {generation.model}")
        print(f"generation_usage: {generation.usage_details}")
        print(f"generation_cost: {generation.cost_details}")
        print("\nWaterfall")
        for item in sorted(group, key=lambda observation: observation.start_time):
            parent = "root" if item.parent_observation_id is None else item.parent_observation_id
            print(
                f"- {item.name} [{item.type}] id={item.id} "
                f"parent={parent} latency_s={item.latency}"
            )

    return 0 if len(valid_traces) >= 10 and pii_hits == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
