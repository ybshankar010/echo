"""Unit tests for echo. Run: python3 -m pytest tests/test_echo.py -q"""
import json
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(REPO, "bin")
sys.path.insert(0, os.path.join(REPO, "lib"))
import echo_common as ec  # noqa: E402


# ---- lib: ticket regex ----

def test_ticket_regex():
    assert ec.TICKET_RE.search("FEAT-3816").group(0) == "FEAT-3816"
    assert ec.TICKET_RE.search("feat/ENG-42/x").group(0) == "ENG-42"
    assert ec.TICKET_RE.search("no ticket here") is None


# ---- lib: stage helpers ----

def test_next_stage():
    assert ec.next_stage("intent") == "spec"
    assert ec.next_stage("ship") == "done"
    assert ec.next_stage("done") is None


def test_new_item_defaults():
    item = ec.new_item("FEAT-1", "t")
    assert item["stage"] == "intent"
    assert item["gates"]["intent"] == "pending"
    assert set(item["gates"]) == set(ec.GATED_STAGES)


# ---- lib: config defaults ----

def test_config_defaults(tmp_path):
    cfg = ec.load_config(str(tmp_path))
    assert cfg["jira_required"] is True
    assert cfg["plan_guard"] == "deny"
    assert cfg["verify_gate"] == "block"


def test_config_maker_checker_defaults(tmp_path):
    cfg = ec.load_config(str(tmp_path))
    assert cfg["build_driver"] == "subagent"
    assert cfg["maker_checker"] == "on"
    assert cfg["maker_checker_max_iters"] == 2
    assert cfg["approve_review"] == "flag"
    assert cfg["autonomy"] == "checkpoint"


# ---- lib: /echo:flow stop-gate rule ----

def test_gate_stops_gated_stops_everywhere():
    assert all(ec.gate_stops("gated", s) for s in ec.GATED_STAGES)


def test_gate_stops_checkpoint():
    assert ec.gate_stops("checkpoint", "plan") is True
    assert ec.gate_stops("checkpoint", "ship") is True
    for s in ("intent", "spec", "build", "test"):
        assert ec.gate_stops("checkpoint", s) is False


def test_gate_stops_auto_only_ship():
    assert ec.gate_stops("auto", "ship") is True
    for s in ("intent", "spec", "plan", "build", "test"):
        assert ec.gate_stops("auto", s) is False


def test_gate_stops_unknown_falls_back_to_checkpoint():
    assert ec.gate_stops("bogus", "plan") is True    # like checkpoint
    assert ec.gate_stops("bogus", "spec") is False


def test_config_merges_missing_keys_over_partial_file(tmp_path):
    # A repo whose config predates the new keys still gets them from defaults.
    ec.ensure_dirs(str(tmp_path))
    ec.save_config({"version": 1, "plan_guard": "warn"}, str(tmp_path))
    cfg = ec.load_config(str(tmp_path))
    assert cfg["plan_guard"] == "warn"           # on-disk value wins
    assert cfg["maker_checker"] == "on"          # missing key filled from defaults
    assert cfg["build_driver"] == "subagent"


# ---- lib: review dir ----

def test_review_dir_path_and_created(tmp_path):
    root = str(tmp_path)
    assert ec.review_dir(root) == os.path.join(root, ".echo", "review")
    ec.ensure_dirs(root)
    assert os.path.isdir(ec.review_dir(root))


# ---- lib: ticket-scoped artifact paths ----

def test_artifact_relpath_is_ticket_scoped():
    assert ec.artifact_relpath("FEAT-3816", "plan") == os.path.join(
        ".echo", "artifacts", "FEAT-3816", "plan.md")


def test_artifact_paths_differ_per_ticket(tmp_path):
    root = str(tmp_path)
    a = ec.artifact_path("FEAT-1", "intent", root)
    b = ec.artifact_path("FEAT-2", "intent", root)
    assert a != b
    assert a == os.path.join(root, ".echo", "artifacts", "FEAT-1", "intent.md")


# ---- lib: research dir + slugify ----

def test_research_dir_path_and_created(tmp_path):
    root = str(tmp_path)
    assert ec.research_dir(root) == os.path.join(root, ".echo", "research")
    ec.ensure_dirs(root)
    assert os.path.isdir(ec.research_dir(root))


def test_slugify_is_deterministic_and_clean():
    assert ec.slugify("Caching Approaches!! v2") == "caching-approaches-v2"
    assert ec.slugify("  leading/trailing  ") == "leading-trailing"
    assert ec.slugify("Caching Approaches!! v2") == ec.slugify("Caching Approaches!! v2")
    assert ec.slugify("") == "untitled"
    assert ec.slugify("!!!") == "untitled"
    assert len(ec.slugify("x" * 200)) <= 60


# ---- lib: jira comment ledger ----

def test_jira_dir_path_and_created(tmp_path):
    root = str(tmp_path)
    assert ec.jira_dir(root) == os.path.join(root, ".echo", "jira")
    ec.ensure_dirs(root)
    assert os.path.isdir(ec.jira_dir(root))


def test_jira_ledger_path_is_per_ticket(tmp_path):
    root = str(tmp_path)
    assert ec.jira_ledger_path("FEAT-9999", root) == os.path.join(
        root, ".echo", "jira", "FEAT-9999.json")


def test_jira_ledger_missing_returns_empty(tmp_path):
    assert ec.load_jira_ledger("FEAT-9999", str(tmp_path)) == {}


def test_jira_ledger_roundtrip(tmp_path):
    root = str(tmp_path)
    ec.save_jira_ledger("FEAT-9999", {"stage:spec": "2026-01-01T00:00:00Z"}, root)
    assert ec.load_jira_ledger("FEAT-9999", root) == {"stage:spec": "2026-01-01T00:00:00Z"}


def test_jira_ledger_corrupt_returns_empty(tmp_path):
    root = str(tmp_path)
    ec.ensure_dirs(root)
    with open(ec.jira_ledger_path("FEAT-9999", root), "w", encoding="utf-8") as fh:
        fh.write("{ not json")
    assert ec.load_jira_ledger("FEAT-9999", root) == {}


def test_jira_ledger_wrong_type_returns_empty(tmp_path):
    # Valid JSON of the wrong type (a list) must coerce to {}, never crash a write.
    root = str(tmp_path)
    ec.ensure_dirs(root)
    with open(ec.jira_ledger_path("FEAT-9999", root), "w", encoding="utf-8") as fh:
        fh.write('["stage:spec"]')
    assert ec.load_jira_ledger("FEAT-9999", root) == {}


# ---- lib: stack detection ----

def test_detect_python(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]\n")
    stacks = ec.detect_stacks(str(tmp_path))
    assert any(s["stack"] == "python" and s["test"] == "pytest" for s in stacks)


def test_detect_js(tmp_path):
    (tmp_path / "package.json").write_text(json.dumps({"scripts": {"test": "jest"}}))
    stacks = ec.detect_stacks(str(tmp_path))
    js = [s for s in stacks if s["stack"] == "js"][0]
    assert js["test"] == "npm test"


def test_detect_gradle(tmp_path):
    (tmp_path / "build.gradle").write_text("")
    stacks = ec.detect_stacks(str(tmp_path))
    assert any(s["test"] == "./gradlew test" for s in stacks)


def test_detect_none(tmp_path):
    assert ec.detect_stacks(str(tmp_path)) == []


# ---- lib: state round-trip ----

def test_state_roundtrip(tmp_path):
    root = str(tmp_path)
    ec.ensure_dirs(root)
    state = ec.default_state()
    state["active"] = "FEAT-9"
    state["items"]["FEAT-9"] = ec.new_item("FEAT-9", "round trip")
    ec.save_state(state, root)
    back = ec.load_state(root)
    assert back["active"] == "FEAT-9"
    assert back["items"]["FEAT-9"]["title"] == "round trip"


# ---- CLI: echo-stage gate behavior ----

def _run(cmd, cwd, stdin=None):
    return subprocess.run(cmd, cwd=cwd, input=stdin, capture_output=True, text=True)


def _init_repo(tmp_path):
    root = str(tmp_path)
    subprocess.run(["git", "init", "-q"], cwd=root)
    _run(["python3", os.path.join(BIN, "echo-stage"), "init",
          "--ticket", "FEAT-3816", "--title", "t"], root)
    return root


def test_stage_next_blocks_until_approved(tmp_path):
    root = _init_repo(tmp_path)
    r = _run(["python3", os.path.join(BIN, "echo-stage"), "next"], root)
    assert r.returncode == 2  # gate pending -> blocked
    _run(["python3", os.path.join(BIN, "echo-stage"), "approve"], root)
    r2 = _run(["python3", os.path.join(BIN, "echo-stage"), "next"], root)
    assert r2.returncode == 0
    assert "advanced:spec" in r2.stdout


def test_set_artifact_derives_ticket_scoped_path(tmp_path):
    root = _init_repo(tmp_path)
    r = _run(["python3", os.path.join(BIN, "echo-stage"), "set-artifact",
              "--stage", "intent"], root)
    assert r.returncode == 0
    rel = os.path.join(".echo", "artifacts", "FEAT-3816", "intent.md")
    assert rel in r.stdout                                   # recorded path is scoped
    assert os.path.isdir(os.path.join(root, ".echo", "artifacts", "FEAT-3816"))  # dir made
    state = ec.load_state(root)
    assert state["items"]["FEAT-3816"]["artifacts"]["intent"] == rel


def test_two_items_do_not_share_artifact_paths(tmp_path):
    root = _init_repo(tmp_path)                              # FEAT-3816 active
    _run(["python3", os.path.join(BIN, "echo-stage"), "set-artifact", "--stage", "intent"], root)
    _run(["python3", os.path.join(BIN, "echo-stage"), "init",
          "--ticket", "NEW-9999", "--title", "second"], root)  # switch active
    _run(["python3", os.path.join(BIN, "echo-stage"), "set-artifact", "--stage", "intent"], root)
    state = ec.load_state(root)
    a = state["items"]["FEAT-3816"]["artifacts"]["intent"]
    b = state["items"]["NEW-9999"]["artifacts"]["intent"]
    assert a != b                                           # no collision across items


def test_research_path_topic_no_state(tmp_path):
    root = str(tmp_path)  # no echo init: research can precede any work item
    r = _run(["python3", os.path.join(BIN, "echo-stage"), "research-path",
              "--topic", "Caching Approaches!! v2"], root)
    assert r.returncode == 0
    assert r.stdout.strip() == os.path.join(".echo", "research", "caching-approaches-v2.md")
    assert os.path.isdir(os.path.join(root, ".echo", "research"))


def test_research_path_ticket_scoped(tmp_path):
    root = _init_repo(tmp_path)
    r = _run(["python3", os.path.join(BIN, "echo-stage"), "research-path",
              "--ticket", "NPI-1234"], root)
    assert r.returncode == 0
    assert r.stdout.strip() == os.path.join(".echo", "artifacts", "NPI-1234", "research.md")
    assert os.path.isdir(os.path.join(root, ".echo", "artifacts", "NPI-1234"))


def test_gate_mode_cli_default_and_explicit(tmp_path):
    root = _init_repo(tmp_path)  # active item at stage intent, default checkpoint
    S = os.path.join(BIN, "echo-stage")
    # explicit stages under checkpoint
    assert _run(["python3", S, "gate-mode", "--stage", "plan"], root).stdout.strip() == "stop"
    assert _run(["python3", S, "gate-mode", "--stage", "ship"], root).stdout.strip() == "stop"
    assert _run(["python3", S, "gate-mode", "--stage", "spec"], root).stdout.strip() == "auto"
    # no --stage defaults to the active item's stage (intent -> auto under checkpoint)
    assert _run(["python3", S, "gate-mode"], root).stdout.strip() == "auto"


def test_gate_mode_cli_no_state_fails_safe_to_stop(tmp_path):
    root = str(tmp_path)  # no echo init, no --stage
    r = _run(["python3", os.path.join(BIN, "echo-stage"), "gate-mode"], root)
    assert r.returncode == 0
    assert r.stdout.strip() == "stop"


# ---- CLI: jira comment gate ----

def test_comment_needed_post_then_skip_after_done(tmp_path):
    root = _init_repo(tmp_path)  # FEAT-3816 active at stage intent
    S = os.path.join(BIN, "echo-stage")
    r = _run(["python3", S, "comment-needed", "--event", "stage:spec"], root)
    assert r.returncode == 0
    assert r.stdout.strip() == "post FEAT-3816"          # fresh event -> post
    d = _run(["python3", S, "comment-done", "--event", "stage:spec"], root)
    assert d.returncode == 0
    r2 = _run(["python3", S, "comment-needed", "--event", "stage:spec"], root)
    assert r2.stdout.strip() == "skip"                    # recorded -> dedup skip
    # the ledger file exists and holds the event
    assert "stage:spec" in ec.load_jira_ledger("FEAT-3816", root)


def test_comment_needed_ticketless_skips(tmp_path):
    # An active item whose key is not a valid ticket -> skip, never post.
    root = str(tmp_path)
    subprocess.run(["git", "init", "-q"], cwd=root)
    ec.ensure_dirs(root)
    state = ec.default_state()
    state["active"] = "topic-caching"
    state["items"]["topic-caching"] = ec.new_item("FEAT-0", "topic")
    ec.save_state(state, root)
    r = _run(["python3", os.path.join(BIN, "echo-stage"),
              "comment-needed", "--event", "stage:spec"], root)
    assert r.returncode == 0
    assert r.stdout.strip() == "skip"


def test_comment_needed_no_state_fails_open(tmp_path):
    root = str(tmp_path)  # no echo init at all
    r = _run(["python3", os.path.join(BIN, "echo-stage"),
              "comment-needed", "--event", "stage:spec"], root)
    assert r.returncode == 0
    assert r.stdout.strip() == "skip"


def test_comment_done_no_state_exits_quietly(tmp_path):
    root = str(tmp_path)  # no echo init
    r = _run(["python3", os.path.join(BIN, "echo-stage"),
              "comment-done", "--event", "stage:spec"], root)
    assert r.returncode == 0


def test_comment_ledger_is_per_ticket(tmp_path):
    # An event recorded for one ticket does not suppress it for another.
    root = _init_repo(tmp_path)  # FEAT-3816 active
    S = os.path.join(BIN, "echo-stage")
    _run(["python3", S, "comment-done", "--event", "stage:spec"], root)
    # switch active to a second ticket
    _run(["python3", S, "init", "--ticket", "NEW-9999", "--title", "second"], root)
    r = _run(["python3", S, "comment-needed", "--event", "stage:spec"], root)
    assert r.stdout.strip() == "post NEW-9999"            # other ticket still due


def test_research_path_requires_exactly_one_selector(tmp_path):
    root = str(tmp_path)
    both = _run(["python3", os.path.join(BIN, "echo-stage"), "research-path",
                 "--ticket", "NPI-1", "--topic", "x"], root)
    assert both.returncode == 2
    neither = _run(["python3", os.path.join(BIN, "echo-stage"), "research-path"], root)
    assert neither.returncode == 2


def test_stage_init_rejects_bad_ticket(tmp_path):
    root = str(tmp_path)
    subprocess.run(["git", "init", "-q"], cwd=root)
    r = _run(["python3", os.path.join(BIN, "echo-stage"), "init",
              "--ticket", "not-a-ticket", "--title", "t"], root)
    assert r.returncode == 2


# ---- CLI: plan-guard ----

def test_plan_guard_blocks_code_allows_md(tmp_path):
    root = _init_repo(tmp_path)
    guard = os.path.join(BIN, "echo-plan-guard")
    code_payload = json.dumps({"tool_input": {"file_path": os.path.join(root, "src/app.py")}})
    r = _run(["python3", guard], root, stdin=code_payload)
    assert r.returncode == 2  # code edit pre-plan blocked
    md_payload = json.dumps({"tool_input": {"file_path": os.path.join(root, ".echo/artifacts/spec.md")}})
    r2 = _run(["python3", guard], root, stdin=md_payload)
    assert r2.returncode == 0  # artifact allowed


def test_plan_guard_fails_open_without_state(tmp_path):
    root = str(tmp_path)  # no .echo, no git
    guard = os.path.join(BIN, "echo-plan-guard")
    payload = json.dumps({"tool_input": {"file_path": os.path.join(root, "x.py")}})
    r = _run(["python3", guard], root, stdin=payload)
    assert r.returncode == 0  # fail open


# ---- CLI: verify + gate ----

def test_verify_and_gate(tmp_path):
    root = _init_repo(tmp_path)
    verify = os.path.join(BIN, "echo-verify")
    gate = os.path.join(BIN, "echo-verify-gate")
    # move to test stage so the gate is active
    _run(["python3", os.path.join(BIN, "echo-stage"), "set-stage", "--stage", "test"], root)
    # failing verify -> gate blocks
    _run(["python3", verify, "--", "false"], root)
    assert _run(["python3", gate], root, stdin="{}").returncode == 2
    # passing verify -> gate allows
    _run(["python3", verify, "--", "true"], root)
    assert _run(["python3", gate], root, stdin="{}").returncode == 0


# ---- CLI: git ship ----

def test_ship_requires_ticket(tmp_path):
    root = str(tmp_path)
    subprocess.run(["git", "init", "-q"], cwd=root)  # no echo state, no ticket branch
    r = _run(["python3", os.path.join(BIN, "echo-git"), "ship", "-m", "x", "--dry-run"], root)
    assert r.returncode == 2


def test_ship_dry_run_with_ticket(tmp_path):
    root = _init_repo(tmp_path)
    r = _run(["python3", os.path.join(BIN, "echo-git"), "ship",
              "-m", "do the thing", "--desc", "thing", "--dry-run"], root)
    assert r.returncode == 0
    assert "FEAT-3816: do the thing" in r.stdout
    assert "Ticket: FEAT-3816" in r.stdout
