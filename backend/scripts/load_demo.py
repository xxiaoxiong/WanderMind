from __future__ import annotations

import argparse
import json
from pathlib import Path

import httpx


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Load the public WanderMind demo dataset")
    parser.add_argument("--api", default="http://localhost:8000/api/v1")
    parser.add_argument("--dataset", type=Path, default=Path("../data/demo_knowledge.jsonl"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    created = 0
    duplicates = 0
    with httpx.Client(base_url=args.api, timeout=30) as client:
        for line in args.dataset.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            item = json.loads(line)
            response = client.post(
                "/knowledge",
                json={
                    "title": item["title"],
                    "content": item["content"],
                    "type": item.get("type", "note"),
                    "source": "demo",
                    "source_ref": item.get("source_ref"),
                    "metadata": {"domain": item.get("domain", "general")},
                },
            )
            if response.status_code == 201:
                created += 1
            elif response.status_code == 409:
                duplicates += 1
            else:
                response.raise_for_status()
    print(f"Loaded {created} items; skipped {duplicates} duplicates")


if __name__ == "__main__":
    main()
