#!/usr/bin/env python3
"""
Per-skill trigger eval runner.

Given ONE skill (SKILL.md frontmatter) and a list of queries with ``should_trigger``
ground truth, asks the model "would this skill fire for this query?" and tallies
precision / recall / F1.

Backend (API vs. ``claude -p``) is chosen by ``evals/_llm.py`` — see its docstring.

Usage:
  # Local (Pro/Max subscription) — no API key needed:
  python evals/trigger/run_trigger_eval.py \\
      --skill cc/skills/hubble_credits \\
      --eval evals/trigger/hubble_credits.json \\
      --variant cc \\
      --out evals/results/trigger-cc-hubble_credits.json

  # With API key (CI or direct):
  export ANTHROPIC_API_KEY=sk-ant-...
  python evals/trigger/run_trigger_eval.py ... (same flags)

Zero runtime deps — Python 3.9+ stdlib only.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# Load sibling helper module (evals/_llm.py).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _llm  # noqa: E402


FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
NAME_RE = re.compile(r"^name:\s*(.+?)\s*$", re.MULTILINE)
DESC_START_RE = re.compile(r"^description:\s*(.*?)\s*$", re.MULTILINE)


def parse_skill_md(path: Path) -> Optional[dict]:
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return None
    m = FRONTMATTER_RE.search(text)
    if not m:
        return None
    fm = m.group(1)
    n, d = NAME_RE.search(fm), DESC_START_RE.search(fm)
    if not (n and d):
        return None
    desc_lines = [d.group(1).strip()]
    for line in fm[d.end():].splitlines():
        if re.match(r"^\s{2,}\S", line):
            desc_lines.append(line.strip())
        elif line.strip() == "":
            continue
        else:
            break
    return {"name": n.group(1).strip(), "description": " ".join(desc_lines).strip()}


# ----- Prompt ----------------------------------------------------------------------

SYSTEM_TEMPLATE = """You are a skill trigger evaluator.

You will receive:
- ONE skill (name + description).
- A user request.

Decide: would this skill fire for this request?

Definitions:
- Fire = the user's intent clearly matches what the skill is designed for.
- Do not fire = off-topic, only surface-level keyword overlap, or a near-miss that belongs to a different tool.

Rules:
- Your reply MUST be a single JSON object and nothing else. No prose before or after.
- The `reason` field MUST be a short plain sentence with all inner quotes escaped.

Skill under test:
- name: {name}
- description: {description}

Output shape:
{{"trigger": true | false, "reason": "<one short sentence>"}}
"""


def build_system(skill: dict) -> str:
    return SYSTEM_TEMPLATE.format(name=skill["name"], description=skill["description"])


def build_user(query: str) -> str:
    return f"User request:\n{query}\n\nReply with the JSON object now."


# ----- Runner -----------------------------------------------------------------------


@dataclass
class CaseResult:
    query: str
    expected: bool
    predicted: Optional[bool]
    ok: bool
    reason: str = ""
    error: str = ""


def run_case(query_item: dict, skill: dict, model: str) -> CaseResult:
    ok, out = _llm.call_model(build_system(skill), build_user(query_item["query"]), model)
    expected = bool(query_item["should_trigger"])
    if not ok:
        return CaseResult(
            query=query_item["query"], expected=expected, predicted=None, ok=False, error=out
        )
    obj = _llm.extract_json_obj(out)
    if obj is None or "trigger" not in obj:
        return CaseResult(
            query=query_item["query"], expected=expected, predicted=None, ok=False,
            error="unparsable-json",
        )
    predicted = bool(obj["trigger"])
    return CaseResult(
        query=query_item["query"],
        expected=expected,
        predicted=predicted,
        ok=(predicted == expected),
        reason=str(obj.get("reason", ""))[:300],
    )


def metrics(results: list[CaseResult]) -> dict:
    tp = sum(1 for r in results if r.expected and r.predicted is True)
    fn = sum(1 for r in results if r.expected and r.predicted is False)
    fp = sum(1 for r in results if not r.expected and r.predicted is True)
    tn = sum(1 for r in results if not r.expected and r.predicted is False)
    errs = sum(1 for r in results if r.predicted is None)
    total = len(results)
    accuracy = (tp + tn) / total if total else 0.0
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return {
        "total": total, "tp": tp, "fp": fp, "tn": tn, "fn": fn, "errors": errs,
        "accuracy": round(accuracy, 3),
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1": round(f1, 3),
    }


DEFAULT_MODEL = os.environ.get("HUBBLE_EVAL_MODEL", "claude-sonnet-4-6")


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skill", required=True, help="Path to skill directory (with SKILL.md)")
    ap.add_argument("--eval", required=True, help="Path to trigger eval JSON")
    ap.add_argument("--variant", default="", help="Label for this run (cc / openclaw / ...)")
    ap.add_argument("--out", required=True, help="Output JSON path")
    ap.add_argument("--workers", type=int, default=int(os.environ.get("HUBBLE_EVAL_WORKERS", "6")))
    ap.add_argument("--model", default=DEFAULT_MODEL, help=f"Anthropic model id (default: {DEFAULT_MODEL})")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args(argv)

    _llm.preflight(fatal=True)

    skill_dir = Path(args.skill)
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        print(f"[err] SKILL.md not found: {skill_md}", file=sys.stderr)
        return 2
    skill = parse_skill_md(skill_md)
    if not skill:
        print(f"[err] failed to parse frontmatter in {skill_md}", file=sys.stderr)
        return 2

    eval_raw = json.loads(Path(args.eval).read_text(encoding="utf-8"))
    # Support both [{"query": ...}, ...] (original) and
    # {"cases": [...], "_tombstone": "..."} (tombstone placeholders).
    if isinstance(eval_raw, dict):
        eval_items = eval_raw.get("cases", [])
    else:
        eval_items = eval_raw

    if not eval_items:
        print(f"[skip] {args.eval} has no cases (tombstone?); writing empty result")
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps(
                {
                    "variant": args.variant,
                    "skill": skill,
                    "model": args.model,
                    "backend": _llm.describe_mode(),
                    "metrics": metrics([]),
                    "elapsed_s": 0.0,
                    "results": [],
                    "_note": "eval file had no cases",
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        return 0

    if args.limit:
        eval_items = eval_items[: args.limit]

    label = f"{args.variant}/{skill['name']}" if args.variant else skill["name"]
    print(f"[info] {label}  model={args.model}  queries={len(eval_items)}  workers={args.workers}")
    print(f"       backend: {_llm.describe_mode()}")

    # CLI mode: `claude -p` subprocess is heavyweight; throttle concurrency.
    if _llm.detect_mode() == "cli" and args.workers > 4:
        print(f"[info] clamping workers {args.workers}→4 for CLI backend", file=sys.stderr)
        effective_workers = 4
    else:
        effective_workers = args.workers

    t0 = time.time()
    results: list[CaseResult] = []
    with cf.ThreadPoolExecutor(max_workers=effective_workers) as ex:
        futs = [ex.submit(run_case, q, skill, args.model) for q in eval_items]
        for i, fut in enumerate(cf.as_completed(futs), start=1):
            r = fut.result()
            results.append(r)
            mark = "✓" if r.ok else "✗"
            exp = "T" if r.expected else "F"
            pred = "—" if r.predicted is None else ("T" if r.predicted else "F")
            print(f"  {mark} [{i:>2}]  exp={exp} got={pred}  {r.query[:80]}")

    order = {q["query"]: i for i, q in enumerate(eval_items)}
    results.sort(key=lambda r: order.get(r.query, 9999))

    m = metrics(results)
    elapsed = time.time() - t0

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_obj = {
        "variant": args.variant,
        "skill": skill,
        "model": args.model,
        "backend": _llm.describe_mode(),
        "metrics": m,
        "elapsed_s": round(elapsed, 2),
        "results": [r.__dict__ for r in results],
    }
    out_path.write_text(json.dumps(out_obj, indent=2, ensure_ascii=False), encoding="utf-8")

    print()
    print(
        f"[done] {label}  acc={m['accuracy']*100:.1f}%  "
        f"P={m['precision']*100:.1f}%  R={m['recall']*100:.1f}%  F1={m['f1']*100:.1f}%  "
        f"errors={m['errors']}  elapsed={elapsed:.1f}s"
    )
    print(f"       json: {out_path}")
    return 0 if m["errors"] == 0 and m["accuracy"] >= 0.85 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
