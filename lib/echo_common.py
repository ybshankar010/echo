"""echo_common — shared helpers for the echo plugin CLIs.

Determinism lives here: repo/.echo paths, the Jira ticket regex, the stage list,
JSON state/config I/O, multi-stack detection, and a thin git runner. Standard
library only (no third-party dependency) so the plugin installs with zero pip.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import time
from typing import Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TICKET_RE = re.compile(r"[A-Z]+-[0-9]+")

# Ordered SDLC stages. `done` is terminal (no artifact/gate of its own).
STAGES = ["intent", "spec", "plan", "build", "test", "ship", "done"]
GATED_STAGES = STAGES[:-1]  # every stage except `done` has an approval gate

STATE_VERSION = 1

DEFAULT_CONFIG = {
    "version": 1,
    "jira_required": True,
    "plan_guard": "deny",         # deny | warn | off
    "plan_guard_override": False,
    "base_branch": "develop",
    "verify_gate": "block",       # block | warn
    "build_driver": "subagent",   # subagent | manual
    "maker_checker": "on",        # on | off
    "maker_checker_max_iters": 2,
    "approve_review": "flag",     # flag | off
    "autonomy": "checkpoint",     # gated | checkpoint | auto (drives /echo:flow)
}

# Which stages /echo:flow stops at for a human approval, per autonomy level.
# A failed automated check always stops, independent of this table.
FLOW_STOP_GATES = {
    "gated": set(GATED_STAGES),        # every gate
    "checkpoint": {"plan", "ship"},    # high-stakes gates only (default)
    "auto": {"ship"},                  # final confirm only
}


def gate_stops(autonomy: str, stage: str) -> bool:
    """True if /echo:flow must stop for human approval at this stage.

    Unknown autonomy falls back to `checkpoint` (fail safe toward more gates).
    """
    stops = FLOW_STOP_GATES.get(autonomy, FLOW_STOP_GATES["checkpoint"])
    return stage in stops


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

def repo_root(start: Optional[str] = None) -> str:
    """Best-effort repo root: git toplevel, else the dir holding .echo, else cwd."""
    start = start or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    # 1) git toplevel
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=start, capture_output=True, text=True,
        )
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    except FileNotFoundError:
        pass
    # 2) walk up for an existing .echo
    cur = os.path.abspath(start)
    while True:
        if os.path.isdir(os.path.join(cur, ".echo")):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent
    # 3) fall back to the starting dir
    return os.path.abspath(start)


def echo_dir(root: Optional[str] = None) -> str:
    return os.path.join(root or repo_root(), ".echo")


def state_path(root: Optional[str] = None) -> str:
    return os.path.join(echo_dir(root), "state.json")


def config_path(root: Optional[str] = None) -> str:
    return os.path.join(echo_dir(root), "config.json")


def artifacts_dir(root: Optional[str] = None) -> str:
    return os.path.join(echo_dir(root), "artifacts")


def artifact_relpath(ticket: str, stage: str) -> str:
    """Repo-relative artifact path, scoped per ticket so items never collide."""
    return os.path.join(".echo", "artifacts", ticket, f"{stage}.md")


def artifact_path(ticket: str, stage: str, root: Optional[str] = None) -> str:
    return os.path.join(root or repo_root(), artifact_relpath(ticket, stage))


def slugify(text: str, maxlen: int = 60) -> str:
    """Deterministic filename slug: lowercase, non-alphanumeric -> '-', trimmed.

    Used for topic-first research filenames so the path is reproducible rather
    than model-invented. Always returns a non-empty slug ('untitled' if empty).
    """
    slug = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    slug = slug[:maxlen].strip("-")
    return slug or "untitled"


def verify_dir(root: Optional[str] = None) -> str:
    return os.path.join(echo_dir(root), "verify")


def review_dir(root: Optional[str] = None) -> str:
    return os.path.join(echo_dir(root), "review")


def research_dir(root: Optional[str] = None) -> str:
    return os.path.join(echo_dir(root), "research")


def jira_dir(root: Optional[str] = None) -> str:
    return os.path.join(echo_dir(root), "jira")


def recap_path(root: Optional[str] = None) -> str:
    return os.path.join(echo_dir(root), "recap.md")


def episodes_path(root: Optional[str] = None) -> str:
    return os.path.join(echo_dir(root), "episodes.jsonl")


def ensure_dirs(root: Optional[str] = None) -> None:
    for d in (echo_dir(root), artifacts_dir(root), verify_dir(root),
              review_dir(root), research_dir(root), jira_dir(root)):
        os.makedirs(d, exist_ok=True)


# ---------------------------------------------------------------------------
# Time
# ---------------------------------------------------------------------------

def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


# ---------------------------------------------------------------------------
# State (JSON)  — owned exclusively by echo-stage / echo-* CLIs
# ---------------------------------------------------------------------------

def _read_json(path: str) -> Optional[dict]:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        return None
    except (json.JSONDecodeError, OSError):
        return None


def _write_json(path: str, data: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, sort_keys=False)
        fh.write("\n")
    os.replace(tmp, path)


def default_state() -> dict:
    return {"version": STATE_VERSION, "active": None, "items": {}}


def load_state(root: Optional[str] = None) -> Optional[dict]:
    """Return the state dict, or None if echo is not initialized in this repo."""
    return _read_json(state_path(root))


def save_state(state: dict, root: Optional[str] = None) -> None:
    _write_json(state_path(root), state)


def load_config(root: Optional[str] = None) -> dict:
    cfg = _read_json(config_path(root))
    if not cfg:
        return dict(DEFAULT_CONFIG)
    merged = dict(DEFAULT_CONFIG)
    merged.update(cfg)
    return merged


def save_config(cfg: dict, root: Optional[str] = None) -> None:
    _write_json(config_path(root), cfg)


# ---------------------------------------------------------------------------
# Jira comment ledger — a committed, per-ticket record of posted events so the
# command layer never posts the same Jira comment twice. Fails open (returns {}
# on a missing/corrupt ledger) so a bad file at worst re-posts one event once.
# ---------------------------------------------------------------------------

def jira_ledger_path(ticket: str, root: Optional[str] = None) -> str:
    return os.path.join(jira_dir(root), f"{ticket}.json")


def load_jira_ledger(ticket: str, root: Optional[str] = None) -> dict:
    data = _read_json(jira_ledger_path(ticket, root))
    # Coerce anything that is not a dict (missing, corrupt, or valid JSON of the
    # wrong type) to {} so callers never crash writing to the ledger. Fail open.
    return data if isinstance(data, dict) else {}


def save_jira_ledger(ticket: str, data: dict, root: Optional[str] = None) -> None:
    _write_json(jira_ledger_path(ticket, root), data)


def new_item(ticket: str, title: str) -> dict:
    ts = now_iso()
    return {
        "title": title,
        "stage": "intent",
        "gates": {s: "pending" for s in GATED_STAGES},
        "artifacts": {"intent": None, "spec": None, "plan": None},
        "created": ts,
        "updated": ts,
    }


def active_item(state: Optional[dict]):
    """Return (ticket, item) for the active item, or (None, None)."""
    if not state or not state.get("active"):
        return None, None
    ticket = state["active"]
    return ticket, state.get("items", {}).get(ticket)


def next_stage(stage: str) -> Optional[str]:
    if stage not in STAGES:
        return None
    i = STAGES.index(stage)
    return STAGES[i + 1] if i + 1 < len(STAGES) else None


# ---------------------------------------------------------------------------
# Git
# ---------------------------------------------------------------------------

def git(*args: str, cwd: Optional[str] = None, check: bool = False):
    """Run a git command, return CompletedProcess. Never raises on non-zero
    unless check=True. Returns a synthetic failure if git is missing."""
    try:
        return subprocess.run(
            ["git", *args], cwd=cwd or repo_root(),
            capture_output=True, text=True, check=check,
        )
    except FileNotFoundError:
        class _Missing:
            returncode = 127
            stdout = ""
            stderr = "git not found"
        return _Missing()


def current_branch(cwd: Optional[str] = None) -> str:
    out = git("branch", "--show-current", cwd=cwd)
    return (out.stdout or "").strip()


def ticket_from_branch(cwd: Optional[str] = None) -> Optional[str]:
    m = TICKET_RE.search(current_branch(cwd))
    return m.group(0) if m else None


# ---------------------------------------------------------------------------
# Stack detection
# ---------------------------------------------------------------------------

def _exists(root: str, *names: str) -> bool:
    return any(os.path.exists(os.path.join(root, n)) for n in names)


def detect_stacks(root: Optional[str] = None) -> list:
    """Return a list of {stack, test, lint} dicts for each detected ecosystem.

    First matching marker per category wins. Empty list means "unknown" and the
    caller must supply an explicit command.
    """
    root = root or repo_root()
    stacks = []

    if _exists(root, "pyproject.toml", "setup.py", "pytest.ini", "tox.ini"):
        # Prefer ruff (fast, common); fall back to flake8 if a flake8 config exists
        # and no ruff config is present.
        if _exists(root, ".flake8", "setup.cfg") and not _exists(root, "ruff.toml", ".ruff.toml"):
            lint = "flake8"
        else:
            lint = "ruff check ."
        stacks.append({"stack": "python", "test": "pytest", "lint": lint})

    if _exists(root, "package.json"):
        pkg = _read_json(os.path.join(root, "package.json")) or {}
        scripts = pkg.get("scripts", {}) if isinstance(pkg, dict) else {}
        runner = "npm"
        if _exists(root, "pnpm-lock.yaml"):
            runner = "pnpm"
        elif _exists(root, "yarn.lock"):
            runner = "yarn"
        test = f"{runner} test" if "test" in scripts else None
        lint = f"{runner} run lint" if "lint" in scripts else None
        stacks.append({"stack": "js", "test": test, "lint": lint})

    if _exists(root, "build.gradle", "build.gradle.kts"):
        stacks.append({"stack": "gradle", "test": "./gradlew test", "lint": None})
    elif _exists(root, "pom.xml"):
        stacks.append({"stack": "maven", "test": "mvn -q test", "lint": None})

    return stacks
