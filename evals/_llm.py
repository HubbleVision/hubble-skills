"""Unified LLM caller for hubble-skills evals.

Two modes, auto-detected at call time:

- **API mode** (preferred for CI / when you have an API key): POST to
  api.anthropic.com via stdlib urllib. Uses an assistant-prefill trick to
  force the model into a JSON object from the first token.
  Triggered when ``ANTHROPIC_API_KEY`` is set in the environment.

- **CLI mode** (default for local dev with a Pro/Max subscription): shell out
  to ``claude --print``. To prevent the user's installed skills, MCP servers,
  and plugins from leaking into the eval call, ``CLAUDE_CONFIG_DIR`` points at
  a per-call temp dir that **mirrors** ``~/.claude/`` via symlinks — except
  that ``skills/``, ``plugins/``, ``mcp-servers/``, ``agents/`` and
  ``commands/`` are replaced by empty stubs. This preserves auth + config
  (Claude Code reads org / user / keychain-lookup metadata from
  ``config.json``) while still keeping the eval environment neutral.
  Triggered when ``ANTHROPIC_API_KEY`` is **not** set and ``claude`` is on
  ``PATH``.

Both paths return the same ``(ok: bool, text: str)`` contract. Downstream JSON
parsing uses :func:`extract_json_obj`, which tolerates markdown fences,
trailing prose, and a small amount of prefix noise.

Zero runtime deps — Python 3.9+ stdlib only.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"


# ----- Mode detection --------------------------------------------------------------

def detect_mode() -> str:
    """Return ``"api"`` if ``ANTHROPIC_API_KEY`` is set, else ``"cli"``."""
    return "api" if os.environ.get("ANTHROPIC_API_KEY") else "cli"


def describe_mode() -> str:
    """One-line human-readable backend description (used by runners in their banners)."""
    if detect_mode() == "api":
        return "api (urllib → api.anthropic.com, prefill-enabled)"
    bin_path = _find_claude() or "<not-found>"
    return f"cli (claude --print, cwd-isolated, bin={bin_path})"


# ----- Main entrypoint -------------------------------------------------------------

def call_model(
    system: str,
    user: str,
    model: str,
    *,
    timeout_s: int = 120,
    max_tokens: int = 512,
    prefill: str = "{",
) -> tuple[bool, str]:
    """Route to the active backend.

    Returns ``(ok, text)``. When ``ok`` is ``True``, ``text`` is the model's
    reply (may still need to be parsed via :func:`extract_json_obj`). When
    ``ok`` is ``False``, ``text`` is a short error description suitable for
    logging in a CaseResult.
    """
    if detect_mode() == "api":
        return _call_api(
            system, user, model,
            timeout_s=timeout_s, max_tokens=max_tokens, prefill=prefill,
        )
    return _call_cli(system, user, model, timeout_s=timeout_s)


# ----- API backend (urllib + prefill) ----------------------------------------------

def _call_api(
    system: str,
    user: str,
    model: str,
    *,
    timeout_s: int,
    max_tokens: int,
    prefill: str,
) -> tuple[bool, str]:
    api_key = os.environ["ANTHROPIC_API_KEY"]
    body = json.dumps(
        {
            "model": model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": [
                {"role": "user", "content": user},
                {"role": "assistant", "content": prefill},
            ],
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        ANTHROPIC_URL,
        data=body,
        headers={
            "x-api-key": api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "content-type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")[:400] if e.fp else ""
        return False, f"HTTP {e.code}: {detail.strip()}"
    except urllib.error.URLError as e:
        return False, f"URLError: {e.reason}"
    except socket.timeout:
        return False, f"timeout after {timeout_s}s"
    except Exception as exc:  # noqa: BLE001 — network calls surprise us regularly
        return False, f"unexpected: {exc!r}"

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        return False, f"non-JSON response: {exc}"

    parts = data.get("content") or []
    text = "".join(p.get("text", "") for p in parts if p.get("type") == "text")
    if not text:
        return False, f"empty response (stop_reason={data.get('stop_reason')})"
    return True, prefill + text


# ----- CLI backend (claude -p with CLAUDE_CONFIG_DIR isolation) --------------------

_CLAUDE_BIN_CACHE: Optional[str] = None


def _find_claude() -> Optional[str]:
    global _CLAUDE_BIN_CACHE
    if _CLAUDE_BIN_CACHE is None:
        _CLAUDE_BIN_CACHE = shutil.which("claude") or ""
    return _CLAUDE_BIN_CACHE or None


def _make_eval_cwd() -> str:
    """Return a path to a fresh empty temp dir to use as the subprocess cwd.

    Rationale: running the claude subprocess from the repo cwd would cause
    Claude Code to pick up the project-local ``.claude/`` directory (CLAUDE.md,
    settings.local.json, etc.), which could skew the eval.  An empty temp dir
    has no ``.claude/`` to load.

    We do NOT override ``CLAUDE_CONFIG_DIR`` here.  In Claude Code ≥ 2.1.x the
    Keychain service key is derived from the config-dir path, so overriding
    ``CLAUDE_CONFIG_DIR`` changes the key, breaks the Keychain lookup, and
    produces "Not logged in".  Auth is handled entirely by the default config
    dir (usually ``~/.claude/``), which is untouched.

    The user's installed skills (``~/.claude/skills/``) are still loaded, but
    the strict "output JSON only" system prompt the runners pass via
    ``--append-system-prompt`` is sufficient to prevent skill execution during
    a routing/trigger evaluation call.

    Safe cleanup: :func:`shutil.rmtree` on the returned path only removes the
    empty temp dir — no real config files are touched.
    """
    return tempfile.mkdtemp(prefix="hubble-eval-claude-")


def _call_cli(
    system: str,
    user: str,
    model: str,
    *,
    timeout_s: int,
) -> tuple[bool, str]:
    claude_bin = _find_claude()
    if not claude_bin:
        return False, (
            "`claude` CLI not on PATH and ANTHROPIC_API_KEY is not set. "
            "Either install Claude Code (https://claude.com/code) and run `claude` "
            "once to log in, or export ANTHROPIC_API_KEY."
        )

    # Use an empty temp dir as cwd so no project-local .claude/ is picked up.
    # CLAUDE_CONFIG_DIR is intentionally NOT overridden: Claude Code ≥ 2.1.x
    # derives the Keychain service key from the config-dir path, so overriding
    # it breaks auth.  See _make_eval_cwd() for the full rationale.
    tmp_cwd = _make_eval_cwd()
    try:
        env = os.environ.copy()
        # Suppress any update nags in -p mode.
        env.setdefault("DISABLE_AUTOUPDATER", "1")

        # Pass the user prompt via stdin instead of as a positional arg so there
        # is no ambiguity with flag ordering across Claude Code versions.
        cmd = [
            claude_bin,
            "--print",
            "--append-system-prompt", system,
            "--model", model,
        ]
        try:
            res = subprocess.run(
                cmd,
                input=user,
                capture_output=True,
                text=True,
                timeout=timeout_s,
                env=env,
                # Run from the empty temp dir to prevent project .claude/ loading.
                cwd=tmp_cwd,
            )
        except subprocess.TimeoutExpired:
            return False, f"timeout after {timeout_s}s (claude -p)"
        except FileNotFoundError:
            return False, f"claude CLI not executable: {claude_bin}"

        if res.returncode != 0:
            tail = (res.stderr or res.stdout or "").strip().splitlines()[-3:]
            joined = " | ".join(tail)[:400]
            return False, f"claude exit {res.returncode}: {joined}"

        out = (res.stdout or "").strip()
        if not out:
            return False, "empty CLI stdout"
        return True, out
    finally:
        shutil.rmtree(tmp_cwd, ignore_errors=True)


# ----- Robust JSON extraction ------------------------------------------------------

_DECODER = json.JSONDecoder()


def extract_json_obj(text: str) -> Optional[dict]:
    """Return the first valid top-level JSON object embedded in text.

    Handles markdown fences, trailing junk after the object, and prefix noise.
    Uses :meth:`json.JSONDecoder.raw_decode` so one stray character past the end
    of the object does not kill us.
    """
    if not text:
        return None
    s = text.strip()
    if s.startswith("```"):
        s = re.sub(r"^```(?:json)?\s*\n?", "", s)
        s = re.sub(r"\n?```\s*$", "", s)

    i = 0
    n = len(s)
    while i < n:
        j = s.find("{", i)
        if j < 0:
            return None
        try:
            obj, _end = _DECODER.raw_decode(s, j)
            if isinstance(obj, dict):
                return obj
            i = j + 1
        except json.JSONDecodeError:
            i = j + 1
    return None


# ----- Preflight -------------------------------------------------------------------

def preflight(fatal: bool = True) -> bool:
    """Verify at least one backend is usable. Print a helpful message if not.

    Returns True on success. If ``fatal`` is True, exits the process with code 2
    on failure; otherwise returns False.
    """
    mode = detect_mode()
    if mode == "api":
        return True
    # CLI mode — make sure the binary is reachable.
    if _find_claude():
        return True
    msg = (
        "[err] no LLM backend available.\n"
        "      Either:\n"
        "        (a) install Claude Code and run `claude` once to log in (Pro/Max auth), OR\n"
        "        (b) export ANTHROPIC_API_KEY=sk-ant-... to use the direct API path."
    )
    if fatal:
        print(msg, file=sys.stderr)
        sys.exit(2)
    print(msg, file=sys.stderr)
    return False
