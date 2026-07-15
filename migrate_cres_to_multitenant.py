import argparse
import hashlib
import json
from pathlib import Path
from typing import Iterable


REQUIRED_FIELDS = {"id"}


def iter_jsonl(path: Path) -> Iterable[dict]:
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def control_hash(item: dict) -> str:
    payload = json.dumps(item, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def simulate(source: Path, report: Path, tenant_id: str, write: bool = False) -> dict:
    seen = set()
    summary = {"read": 0, "valid": 0, "duplicates": 0, "missing_required": 0, "write_requested": write}
    rows = []
    for item in iter_jsonl(source):
        summary["read"] += 1
        missing = sorted(field for field in REQUIRED_FIELDS if not item.get(field))
        duplicate = item.get("id") in seen
        if duplicate:
            summary["duplicates"] += 1
        if missing:
            summary["missing_required"] += 1
        if not duplicate and not missing:
            summary["valid"] += 1
        seen.add(item.get("id"))
        migrated = dict(item)
        migrated["tenant_id"] = tenant_id
        rows.append(
            {
                "id": item.get("id"),
                "valid": not duplicate and not missing,
                "duplicate": duplicate,
                "missing": missing,
                "hash": control_hash(migrated),
            }
        )
    report.write_text(json.dumps({"summary": summary, "rows": rows}, indent=2), encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-jsonl", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--tenant-id", default="cres")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    if args.write:
        raise RuntimeError("Write mode is intentionally not implemented in phase 1.")
    summary = simulate(Path(args.source_jsonl), Path(args.report), args.tenant_id, write=args.write)
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
