#!/usr/bin/env python3
"""
Cross-skill routing eval runner for hubble-skills.

For each prompt in routing_eval.json:
  - Load all SKILL.md descriptions under a given skills/ directory
  - Ask the model which skill (if any) should be invoked
  - Compare the model's choice to the expected skill and tally accuracy

Runs per variant (cc / openclaw) and writes a results JSON + pretty Markdown.

Backend is chosen by ``evals/_llm.py``:
  - If ANTHROPIC_API_KEY is set → direct API via urllib (prefill-enabled).
  - Else → ``claude -p`` with CLAUDE_CONFIG_DIR isolation so installed skills
    at ~/.claude/skills/ don't pollute the call.

Usage:
  # Local (Pro/Max subscription) — no API key needed:
  python evals/routing/run_routing_eval.py --skills-root cc/skills --variant cc \\
      --out evals/results/routing-cc.json

  # CI / with an API key:
  export ANTHROPIC_API_KEY=sk-ant-...
  python evals/routing/run_routing_eval.py --skills-root cc/skills --variant cc \\
      --out evals/results/routing-cc.json

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

# Make `import _llm` work whether invoked as `python evals/routing/run_routing_eval.py`
# or via its absolute path in CI.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _llm  # noqa: E402 — intentional sys.path tweak above


# ----- SKILL.md frontmatter parsing -------------------------------------------------

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
NAME_RE = re.compile(r"^name:\s*(.+?)\s*$", re.MULTILINE)
DESC_START_RE = re.compile(r"^description:\s*(.*?)\s*$", re.MULTILINE)


def parse_skill_md(path: Path) -> Optional[dict]:
    """Extract {name, description} from a SKILL.md file."""
    try:
        text = path.read_text(encoding="utf-8")
    except Exception as exc:
        print(f"[warn] failed to read {path}: {exc}", file=sys.stderr)
        return None
    m = FRONTMATTER_RE.search(text)
    if not m:
        # Skill files without frontmatter (e.g. tombstones) are silently skipped.
        return None
    fm = m.group(1)
    name_m = NAME_RE.search(fm)
    desc_m = DESC_START_RE.search(fm)
    if not (name_m and desc_m):
        return None
    desc_lines = [desc_m.group(1).strip()]
    tail = fm[desc_m.end():]
    for line in tail.splitlines():
        if re.match(r"^\s{2,}\S", line):
            desc_lines.append(line.strip())
        elif line.strip() == "":
            continue
        else:
            break
    description = " ".join(desc_lines).strip()
    return {"name": name_m.group(1).strip(), "description": description}


def load_skills(root: Path) -> list[dict]:
    skills = []
    for skill_md in sorted(root.glob("*/SKILL.md")):
        meta = parse_skill_md(skill_md)
        if meta:
            skills.append(meta)
    return skills


# ----- Prompt templates -------------------------------------------------------------

ROUTER_SYSTEM_TEMPLATE = """You are a deterministic skill router.

You will receive:
- A list of available skills, each with a `name` and a `description`.
- A user request.

Your job: pick the SINGLE skill whose description best matches the user request, OR return null if none matches.

Rules:
- Match by intent, not by surface keywords.
- If two skills look close, pick the one that is more specific to the user's action.
- If the request is off-topic relative to every skill, return null.
- Do not invent skill names. Only return a name that appears in the list.
- Your reply MUST be a single JSON object and nothing else. No prose before or after.
- The JSON's `reason` field MUST be a short sentence with all inner quotes escaped.

Available skills:
{catalog}

Output shape:
{{"skill": "<skill_name_or_null>", "reason": "<one short sentence>"}}
"""


def build_system(skills: list[dict]) -> str:
    catalog = "\n".join(
        f"- name: {s['name']}\n  description: {s['description']}" for s in skills
    )
    return ROUTER_SYSTEM_TEMPLATE.format(catalog=catalog)


def build_user(user_request: str) -> str:
    return f"User request:\n{user_request}\n\nReply with the JSON object now."


# ----- Runner -----------------------------------------------------------------------


@dataclass
class CaseResult:
    id: str
    category: str
    prompt: str
    expected: Optional[str]
    predicted: Optional[str]
    reason: str = ""
    ok: bool = False
    raw: str = ""
    error: str = ""


def run_case(case: dict, skills: list[dict], model: str, dry_run: bool) -> CaseResult:
    system = build_system(skills)
    user = build_user(case["prompt"])
    expected = case.get("expected")

    if dry_run:
        return CaseResult(
            id=case["id"],
            category=case.get("category", ""),
            prompt=case["prompt"],
            expected=expected,
            predicted=None,
            reason="(dry-run)",
            ok=False,
            error="dry-run",
        )

    ok, out = _llm.call_model(system, user, model)
    if not ok:
        return CaseResult(
            id=case["id"],
            category=case.get("category", ""),
            prompt=case["prompt"],
            expected=expected,
            predicted=None,
            error=out,
        )

    obj = _llm.extract_json_obj(out)
    if obj is None:
        return CaseResult(
            id=case["id"],
            category=case.get("category", ""),
            prompt=case["prompt"],
            expected=expected,
            predicted=None,
            raw=out[:500],
            error="unparsable-json",
        )

    predicted_raw = obj.get("skill")
    predicted = (
        None if predicted_raw in (None, "", "null", "none") else str(predicted_raw)
    )
    reason = str(obj.get("reason", ""))[:300]

    ok_match = (
        predicted == expected if expected is not None else predicted is None
    )

    return CaseResult(
        id=case["id"],
        category=case.get("category", ""),
        prompt=case["prompt"],
        expected=expected,
        predicted=predicted,
        reason=reason,
        ok=ok_match,
        raw=out[:500],
    )


def tally(results: list[CaseResult]) -> dict:
    total = len(results)
    passed = sum(1 for r in results if r.ok)
    by_cat: dict[str, dict] = {}
    for r in results:
        b = by_cat.setdefault(r.category, {"total": 0, "pass": 0})
        b["total"] += 1
        if r.ok:
            b["pass"] += 1
    return {
        "total": total,
        "pass": passed,
        "pass_rate": round(passed / total, 3) if total else 0.0,
        "by_category": by_cat,
    }


def format_markdown(summary: dict, results: list[CaseResult], variant: str, model: str) -> str:
    lines = [f"# Routing eval — {variant}", ""]
    lines.append(f"- model: `{model}`")
    lines.append(f"- backend: `{_llm.describe_mode()}`")
    lines.append(f"- total: **{summary['total']}**")
    lines.append(f"- pass:  **{summary['pass']}**")
    lines.append(f"- pass_rate: **{summary['pass_rate']*100:.1f}%**")
    lines.append("")
    lines.append("## By category")
    lines.append("| category | pass | total | rate |")
    lines.append("|---|---|---|---|")
    for cat, b in sorted(summary["by_category"].items()):
        rate = (b["pass"] / b["total"] * 100) if b["total"] else 0.0
        lines.append(f"| {cat} | {b['pass']} | {b['total']} | {rate:.1f}% |")
    lines.append("")
    lines.append("## Failures")
    lines.append("| id | category | prompt | expected | predicted | reason/error |")
    lines.append("|---|---|---|---|---|---|")
    for r in results:
        if r.ok:
            continue
        exp = r.expected or "—"
        pred = r.predicted or "—"
        why = (r.error or r.reason).replace("|", "\\|").replace("\n", " ")
        p = r.prompt.replace("|", "\\|")
        lines.append(f"| {r.id} | {r.category} | {p} | {exp} | {pred} | {why} |")
    lines.append("")
    return "\n".join(lines)


DEFAULT_MODEL = os.environ.get("HUBBLE_EVAL_MODEL", "claude-sonnet-4-6")


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skills-root", required=True, help="Path to */skills directory (e.g. cc/skills)")
    ap.add_argument("--variant", required=True, help="Label for this run (cc / openclaw / ...)")
    ap.add_argument("--eval", default="evals/routing/routing_eval.json")
    ap.add_argument("--out", default="evals/results/routing.json")
    ap.add_argument("--workers", type=int, default=int(os.environ.get("HUBBLE_EVAL_WORKERS", "6")))
    ap.add_argument("--model", default=DEFAULT_MODEL, help=f"Anthropic model id (default: {DEFAULT_MODEL})")
    ap.add_argument("--dry-run", action="store_true", help="Print resolved skills + first prompt, then exit.")
    ap.add_argument("--limit", type=int, default=0, help="If >0, only run the first N cases.")
    args = ap.parse_args(argv)

    if not args.dry_run:
        _llm.preflight(fatal=True)

    skills_root = Path(args.skills_root)
    if not skills_root.is_dir():
        print(f"[err] --skills-root not a directory: {skills_root}", file=sys.stderr)
        return 2

    skills = load_skills(skills_root)
    if not skills:
        print(f"[err] no skills found under {skills_root}", file=sys.stderr)
        return 2

    eval_path = Path(args.eval)
    eval_data = json.loads(eval_path.read_text(encoding="utf-8"))
    cases = eval_data["cases"]
    if args.limit:
        cases = cases[: args.limit]

    print(
        f"[info] variant={args.variant}  model={args.model}  "
        f"skills={len(skills)}  cases={len(cases)}  workers={args.workers}"
    )
    print(f"       backend: {_llm.describe_mode()}")
    for s in skills:
        print(f"       - {s['name']}")

    if args.dry_run:
        print("\n[dry-run] system prompt (truncated):\n")
        print(build_system(skills)[:1200])
        print("\n[dry-run] first user message:\n")
        print(build_user(cases[0]["prompt"]))
        return 0

    # In CLI mode, each call spins up a `claude -p` subprocess — concurrency
    # above ~4 tends to thrash. API mode happily runs at 6+.
    if _llm.detect_mode() == "cli" and args.workers > 4:
        print(f"[info] clamping workers {args.workers}→4 for CLI backend", file=sys.stderr)
        effective_workers = 4
    else:
        effective_workers = args.workers

    t0 = time.time()
    results: list[CaseResult] = []
    with cf.ThreadPoolExecutor(max_workers=effective_workers) as ex:
        futs = {ex.submit(run_case, c, skills, args.model, False): c for c in cases}
        for fut in cf.as_completed(futs):
            r = fut.result()
            results.append(r)
            mark = "✓" if r.ok else "✗"
            tag = f"[{r.error}]" if r.error else ""
            print(
                f"  {mark}  {r.id:<15}  exp={r.expected or 'none':<15}  "
                f"got={r.predicted or 'none':<15}  {tag}"
            )

    # Keep deterministic case order.
    order = {c["id"]: i for i, c in enumerate(cases)}
    results.sort(key=lambda r: order.get(r.id, 9999))

    summary = tally(results)
    elapsed = time.time() - t0

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_obj = {
        "variant": args.variant,
        "model": args.model,
        "backend": _llm.describe_mode(),
        "skills": [s["name"] for s in skills],
        "skills_root": str(skills_root),
        "summary": summary,
        "elapsed_s": round(elapsed, 2),
        "results": [r.__dict__ for r in results],
    }
    out_path.write_text(json.dumps(out_obj, indent=2, ensure_ascii=False), encoding="utf-8")

    md_path = out_path.with_suffix(".md")
    md_path.write_text(
        format_markdown(summary, results, args.variant, args.model), encoding="utf-8"
    )

    print()
    print(
        f"[done] variant={args.variant}  pass={summary['pass']}/{summary['total']}  "
        f"rate={summary['pass_rate']*100:.1f}%  elapsed={elapsed:.1f}s"
    )
    print(f"       json: {out_path}")
    print(f"       md:   {md_path}")

    return 0 if summary["pass"] == summary["total"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
