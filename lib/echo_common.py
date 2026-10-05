"""echo_common - shared helpers for the echo plugin CLIs.

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
    "watch_gate": "block",        # block | warn | off (post-ship CI/review watch)
    "review_bot_login": "",       # GitHub login whose review comments alert Jira
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


def watch_artifact_relpath(ticket: str) -> str:
    """Repo-relative path for the post-ship CI/review watch artifact."""
    return os.path.join(".echo", "verify", f"{ticket}-ci.md")


def watch_artifact_path(ticket: str, root: Optional[str] = None) -> str:
    return os.path.join(root or repo_root(), watch_artifact_relpath(ticket))


def parse_checks(data: list):
    """Map a parsed `gh pr checks --json bucket,state,name,link` list to a
    (result, failing_names) tuple. Pure: no network, no subprocess.

    - any check in the `pending` bucket -> ("pending", [failing names])
    - else any check in the `fail` bucket -> ("fail", [failing names])
    - else -> ("pass", [])
    - empty list -> ("pending", []) (a just-opened PR with no checks yet)
    """
    if not data:
        return "pending", []
    failing = [c.get("name", "") for c in data if c.get("bucket") == "fail"]
    if any(c.get("bucket") == "pending" for c in data):
        return "pending", failing
    if failing:
        return "fail", failing
    return "pass", []


# ---------------------------------------------------------------------------
# Plan "Order of work" checklist: pure text helpers (no IO). The plan's
# "## Order of work" section is authored as a GitHub checkbox list; these parse,
# count, and toggle it. Only that section is treated as the checklist so
# incidental checkboxes elsewhere (e.g. in Proof) are never counted or touched.
# ---------------------------------------------------------------------------

_ORDER_HEADING_RE = re.compile(r"^##\s+Order of work")
_ANY_H2_RE = re.compile(r"^##\s")
_CHECKBOX_RE = re.compile(r"^\s*-\s+\[( |x|X)\]\s+(.*)$")


def parse_order_checklist(text: str) -> list:
    """Parse the plan's `## Order of work` checkbox list into an ordered list of
    {index (1-based), checked (bool), text}. Scans only the section under the
    `## Order of work` heading (up to the next `## ` heading or end of file).
    No section, or none matching, returns []. Pure: no IO.
    """
    items = []
    in_section = False
    idx = 0
    for line in (text or "").splitlines():
        if _ORDER_HEADING_RE.match(line):
            in_section = True
            continue
        if in_section and _ANY_H2_RE.match(line):
            break
        if in_section:
            m = _CHECKBOX_RE.match(line)
            if m:
                idx += 1
                items.append({
                    "index": idx,
                    "checked": m.group(1) in ("x", "X"),
                    "text": m.group(2),
                })
    return items


def checklist_counts(items) -> tuple:
    """Return (done, total) for a parsed checklist."""
    return sum(1 for i in items if i["checked"]), len(items)


def set_checkbox(text: str, index: int, checked: bool) -> str:
    """Return `text` with only the marker char of the 1-based index-th
    Order-of-work checkbox line rewritten ([ ]->[x] or back); everything else is
    byte-identical. Out-of-range index returns `text` unchanged. Pure: no IO.
    """
    lines = (text or "").splitlines(keepends=True)
    in_section = False
    idx = 0
    marker = "x" if checked else " "
    for i, line in enumerate(lines):
        if _ORDER_HEADING_RE.match(line):
            in_section = True
            continue
        if in_section and _ANY_H2_RE.match(line):
            break
        if in_section and _CHECKBOX_RE.match(line):
            idx += 1
            if idx == index:
                lines[i] = re.sub(r"\[( |x|X)\]", f"[{marker}]", line, count=1)
                return "".join(lines)
    return text


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
# State (JSON) - owned exclusively by echo-stage / echo-* CLIs
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
# Jira comment ledger - a committed, per-ticket record of posted events so the
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


# ---------------------------------------------------------------------------
# Review threads - GitHub PR review-thread enumeration/resolution support for
# /echo:address-review. Determinism (gh calls, JSON parsing, the per-thread
# ledger) lives here; the orchestration lives in commands/address-review.md.
# Fails open: a missing/unauthenticated/hung gh yields None, never a raise.
# ---------------------------------------------------------------------------

# Per-call wall-clock cap so a single hung gh read (network hang, auth prompt,
# outage) cannot block forever. Mirrors echo-watch's GH_CALL_TIMEOUT.
GH_CALL_TIMEOUT = 30


def one_line(body: str, maxlen: int = 200) -> str:
    """Collapse a comment body to a single truncated line. Never keeps a diff,
    token, or secret past the cap. Mirrors echo-watch._one_line so artifacts
    stay one-line only."""
    text = " ".join((body or "").split())
    return text[:maxlen]


def _parse_pr_view(text: str) -> Optional[dict]:
    """Pure parse of `gh pr view --json number,url,headRefOid` output into
    {number, url, head_sha}, or None if the payload is missing a PR number."""
    try:
        data = json.loads(text)
    except (ValueError, TypeError):
        return None
    if not isinstance(data, dict) or "number" not in data:
        return None
    return {
        "number": data.get("number"),
        "url": data.get("url", ""),
        "head_sha": data.get("headRefOid", ""),
    }


def _parse_repo_view(text: str) -> Optional[dict]:
    """Pure parse of `gh repo view --json owner,name` output into
    {owner, repo}, or None if owner/name cannot be read."""
    try:
        data = json.loads(text)
    except (ValueError, TypeError):
        return None
    if not isinstance(data, dict):
        return None
    owner = data.get("owner")
    if isinstance(owner, dict):
        owner = owner.get("login")
    name = data.get("name")
    if not owner or not name:
        return None
    return {"owner": owner, "repo": name}


def resolve_pr(cwd: Optional[str] = None) -> Optional[dict]:
    """Return {number, url, head_sha, owner, repo} for the checked-out branch's
    open PR, or None. Resolves by branch (not by ticket) via `gh pr view` and
    `gh repo view`. Fails closed to None on any error (no gh, no auth, no PR)."""
    cwd = cwd or repo_root()

    def _gh(args):
        try:
            return subprocess.run(["gh", *args], cwd=cwd, capture_output=True,
                                  text=True, timeout=GH_CALL_TIMEOUT)
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            return None

    r = _gh(["pr", "view", "--json", "number,url,headRefOid"])
    if r is None or r.returncode != 0:
        return None
    pr = _parse_pr_view(r.stdout)
    if pr is None:
        return None
    r2 = _gh(["repo", "view", "--json", "owner,name"])
    if r2 is None or r2.returncode != 0:
        return None
    repo = _parse_repo_view(r2.stdout)
    if repo is None:
        return None
    return {
        "number": pr["number"],
        "url": pr["url"],
        "head_sha": pr["head_sha"],
        "owner": repo["owner"],
        "repo": repo["repo"],
    }


def gh(args, cwd=None, timeout=GH_CALL_TIMEOUT):
    """Run `gh` with args; return the CompletedProcess, or None on any failure
    (gh missing, timeout, OS error). Fails open so callers never raise on a
    missing or hung gh. Auth is delegated to gh; this never reads or logs a
    token. Shared plumbing so new CLIs need no private `_gh`."""
    try:
        return subprocess.run(["gh", *args], cwd=cwd, capture_output=True,
                              text=True, timeout=timeout)
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return None


def gh_json(args, cwd=None):
    """Run `gh args` and parse stdout as JSON. Return the parsed object, or
    None on any failure (gh missing/hung, non-zero exit, unparseable output)."""
    r = gh(args, cwd=cwd)
    if r is None or r.returncode != 0:
        return None
    try:
        return json.loads(r.stdout)
    except (ValueError, TypeError):
        return None


def _parse_pr_view_full(text: str) -> Optional[dict]:
    """Pure parse of `gh pr view <pr> --json
    number,baseRefName,headRefName,headRefOid,url,isCrossRepository,title,body`
    into a normalized dict, or None if the payload lacks a PR number."""
    try:
        data = json.loads(text)
    except (ValueError, TypeError):
        return None
    if not isinstance(data, dict) or "number" not in data:
        return None
    return {
        "number": data.get("number"),
        "base_ref": data.get("baseRefName", ""),
        "head_ref": data.get("headRefName", ""),
        "head_sha": data.get("headRefOid", ""),
        "url": data.get("url", ""),
        "is_cross_repository": bool(data.get("isCrossRepository", False)),
        "title": data.get("title", ""),
        "body": data.get("body", ""),
    }


def _parse_owner_repo_from_url(url) -> Optional[dict]:
    """Pure parse of a GitHub PR/issue url like
    https://github.com/<owner>/<repo>/pull/<n> into {owner, repo}, or None when
    the url carries no owner/repo path. Host-agnostic (works for GH Enterprise)
    because it keys off the /pull/ or /issues/ segment, not the hostname."""
    if not isinstance(url, str) or not url:
        return None
    m = re.search(r"[:/]([^/]+)/([^/]+)/(?:pull|issues)/\d+", url)
    if not m:
        return None
    return {"owner": m.group(1), "repo": m.group(2)}


def _reconcile_pr_repo(parsed: dict, cwd_repo: dict) -> Optional[dict]:
    """Reconcile the PR url's owner/repo against the cwd repo. `gh pr view <url>`
    resolves the url's repo while the fetch/post run against the cwd repo, so a
    url pointing at a different repo would silently review or POST the wrong PR.
    When the url names a repo that differs from the cwd repo, return None (fail
    closed). Otherwise return {owner, repo} (the url's when present, else cwd's),
    so a plain PR number keeps working against the cwd repo. Pure."""
    url_repo = _parse_owner_repo_from_url(parsed.get("url", ""))
    if url_repo is not None:
        if (url_repo["owner"] != cwd_repo["owner"]
                or url_repo["repo"] != cwd_repo["repo"]):
            return None
        return url_repo
    return cwd_repo


def resolve_pr_by_number(pr, cwd: Optional[str] = None) -> Optional[dict]:
    """Resolve an explicit PR (url or number) in the repo at cwd into
    {number, owner, repo, base_ref, head_sha, head_ref, is_cross_repository,
    title, body}, or None. Runs `gh pr view <pr> --json ...` plus
    `gh repo view --json owner,name`. Fails closed to None on any error (no gh,
    no auth, no remote, unresolvable PR) and on a url-vs-cwd repo mismatch, so a
    url pointing at a different repo never reviews or POSTs the wrong PR.
    Separate from the branch-based resolve_pr, which is left unchanged."""
    cwd = cwd or repo_root()
    r = gh(["pr", "view", str(pr), "--json",
            "number,baseRefName,headRefName,headRefOid,url,"
            "isCrossRepository,title,body"], cwd=cwd)
    if r is None or r.returncode != 0:
        return None
    parsed = _parse_pr_view_full(r.stdout)
    if parsed is None:
        return None
    r2 = gh(["repo", "view", "--json", "owner,name"], cwd=cwd)
    if r2 is None or r2.returncode != 0:
        return None
    repo = _parse_repo_view(r2.stdout)
    if repo is None:
        return None
    final = _reconcile_pr_repo(parsed, repo)
    if final is None:
        return None  # url names a different repo than cwd -> fail closed
    parsed["owner"] = final["owner"]
    parsed["repo"] = final["repo"]
    return parsed


def _thread_nodes(data) -> list:
    """Dig the reviewThreads nodes list out of a decoded GraphQL response,
    accepting either the full response, the inner repository shape, or a bare
    nodes list. Returns [] on any unexpected shape. Pure."""
    if isinstance(data, list):
        return data
    if not isinstance(data, dict):
        return []
    cur = data
    if isinstance(cur.get("data"), dict):
        cur = cur["data"]
    for key in ("repository", "pullRequest", "reviewThreads"):
        if not isinstance(cur, dict):
            return []
        cur = cur.get(key, {})
    if isinstance(cur, dict):
        nodes = cur.get("nodes")
        return nodes if isinstance(nodes, list) else []
    return []


def parse_review_threads(data) -> list:
    """Pure function over decoded GraphQL JSON
    (repository.pullRequest.reviewThreads.nodes) -> a list of
    {id, is_resolved, is_outdated, path, line, author, body_oneline, url}.
    Author/body/url come from the FIRST comment in each thread; the body is
    truncated to one line via one_line so no diff/token/secret is stored. Pure:
    no IO."""
    threads = []
    for node in _thread_nodes(data):
        if not isinstance(node, dict):
            continue
        comments = ((node.get("comments") or {}).get("nodes")) or []
        first = comments[0] if comments and isinstance(comments[0], dict) else {}
        author = (first.get("author") or {}).get("login") or ""
        threads.append({
            "id": node.get("id", ""),
            "is_resolved": bool(node.get("isResolved")),
            "is_outdated": bool(node.get("isOutdated")),
            "path": node.get("path") or "",
            "line": node.get("line"),
            "author": author,
            "body_oneline": one_line(first.get("body")),
            "url": first.get("url") or "",
        })
    return threads


# ---------------------------------------------------------------------------
# Review-thread ledger - a committed, per-ticket record of thread node id ->
# {status, ts, commit} so /echo:address-review skips already-resolved threads
# and re-runs are idempotent. Mirrors the Jira ledger helpers; fails open.
# ---------------------------------------------------------------------------

def thread_ledger_path(ticket: str, root: Optional[str] = None) -> str:
    return os.path.join(review_dir(root), f"{ticket}-threads.json")


def load_thread_ledger(ticket: str, root: Optional[str] = None) -> dict:
    data = _read_json(thread_ledger_path(ticket, root))
    # Coerce anything that is not a dict to {} so callers never crash writing to
    # the ledger. Fail open.
    return data if isinstance(data, dict) else {}


def save_thread_ledger(ticket: str, data: dict, root: Optional[str] = None) -> None:
    _write_json(thread_ledger_path(ticket, root), data)


def review_comments_relpath(ticket: str) -> str:
    """Repo-relative path for the human-readable review-threads artifact."""
    return os.path.join(".echo", "review", f"{ticket}-comments.md")


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
