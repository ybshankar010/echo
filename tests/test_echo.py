"""Unit tests for echo. Run: python3 -m pytest tests/test_echo.py -q"""
import importlib.machinery
import importlib.util
import json
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(REPO, "bin")
sys.path.insert(0, os.path.join(REPO, "lib"))
import echo_common as ec  # noqa: E402


def _load_watch_module():
    """Import bin/echo-watch (no .py extension) as a module so its helpers can
    be unit-tested in-process without shelling out or touching the network."""
    path = os.path.join(BIN, "echo-watch")
    loader = importlib.machinery.SourceFileLoader("echo_watch", path)
    spec = importlib.util.spec_from_loader("echo_watch", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


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


# ---- lib: watch config defaults + artifact path ----

def test_config_watch_defaults(tmp_path):
    cfg = ec.load_config(str(tmp_path))
    assert cfg["watch_gate"] == "block"
    assert "review_bot_login" in cfg
    assert cfg["review_bot_login"] == ""


def test_watch_artifact_path_is_ci_scoped(tmp_path):
    root = str(tmp_path)
    assert ec.watch_artifact_relpath("FEAT-1") == os.path.join(
        ".echo", "verify", "FEAT-1-ci.md")
    p = ec.watch_artifact_path("FEAT-1", root)
    assert p == os.path.join(root, ".echo", "verify", "FEAT-1-ci.md")
    assert p.endswith(os.path.join(".echo", "verify", "FEAT-1-ci.md"))


# ---- lib: pure CI check parsing ----

def test_parse_checks_all_pass():
    data = [{"bucket": "pass", "name": "build"}, {"bucket": "pass", "name": "lint"}]
    assert ec.parse_checks(data) == ("pass", [])


def test_parse_checks_one_fail():
    data = [{"bucket": "pass", "name": "build"}, {"bucket": "fail", "name": "lint"}]
    assert ec.parse_checks(data) == ("fail", ["lint"])


def test_parse_checks_pending_wins():
    data = [{"bucket": "fail", "name": "lint"}, {"bucket": "pending", "name": "e2e"}]
    result, failing = ec.parse_checks(data)
    assert result == "pending"
    assert "lint" in failing


def test_parse_checks_empty_is_pending():
    assert ec.parse_checks([]) == ("pending", [])


# ---- lib: Order-of-work checklist pure helpers ----

_PLAN_FIXTURE = (
    "# Plan\n\n"
    "## Order of work\n"
    "- [ ] 1. first step\n"
    "- [x] 2. second step\n"
    "- [ ] 3. third step\n\n"
    "## Proof\n"
    "- [ ] not a work item, must be ignored\n"
)


def test_parse_order_checklist_only_order_section():
    items = ec.parse_order_checklist(_PLAN_FIXTURE)
    assert [i["index"] for i in items] == [1, 2, 3]        # Proof checkbox excluded
    assert [i["checked"] for i in items] == [False, True, False]
    assert items[0]["text"] == "1. first step"


def test_parse_order_checklist_missing_section_is_empty():
    assert ec.parse_order_checklist("# Plan\n\n## Files\n- [ ] x\n") == []
    assert ec.parse_order_checklist("") == []


def test_parse_order_checklist_no_checkboxes_is_empty():
    assert ec.parse_order_checklist("## Order of work\n1. plain numbered\n") == []


def test_checklist_counts():
    items = ec.parse_order_checklist(_PLAN_FIXTURE)
    assert ec.checklist_counts(items) == (1, 3)
    assert ec.checklist_counts([]) == (0, 0)


def test_set_checkbox_flips_only_marker_and_preserves_text():
    out = ec.set_checkbox(_PLAN_FIXTURE, 1, True)
    assert "- [x] 1. first step\n" in out                  # marker set
    assert "- [ ] 2." not in out                           # item 2 (already [x]) untouched
    # Only the single marker char changed: the rest of the file is byte-identical.
    assert out == _PLAN_FIXTURE.replace("- [ ] 1. first step", "- [x] 1. first step", 1)


def test_set_checkbox_uncheck_roundtrip():
    checked = ec.set_checkbox(_PLAN_FIXTURE, 1, True)
    back = ec.set_checkbox(checked, 1, False)
    assert back == _PLAN_FIXTURE                            # exact restore


def test_set_checkbox_out_of_range_is_noop():
    assert ec.set_checkbox(_PLAN_FIXTURE, 0, True) == _PLAN_FIXTURE
    assert ec.set_checkbox(_PLAN_FIXTURE, 99, True) == _PLAN_FIXTURE
    assert ec.set_checkbox(_PLAN_FIXTURE, 4, True) == _PLAN_FIXTURE  # Proof box not reachable


def test_set_checkbox_never_touches_proof_section():
    out = ec.set_checkbox(_PLAN_FIXTURE, 3, True)
    assert "- [ ] not a work item, must be ignored\n" in out  # Proof checkbox unchanged


# ---- CLI: echo-stage checklist / check / uncheck / check-next ----

def _init_repo_with_plan(tmp_path, body=None):
    root = _init_repo(tmp_path)
    plan_dir = os.path.join(root, ".echo", "artifacts", "FEAT-3816")
    os.makedirs(plan_dir, exist_ok=True)
    with open(os.path.join(plan_dir, "plan.md"), "w", encoding="utf-8") as fh:
        fh.write(body if body is not None else _PLAN_FIXTURE)
    _run(["python3", os.path.join(BIN, "echo-stage"), "set-artifact",
          "--stage", "plan"], root)
    return root


def _plan_text(root):
    with open(os.path.join(root, ".echo", "artifacts", "FEAT-3816", "plan.md"),
              encoding="utf-8") as fh:
        return fh.read()


def test_cli_checklist_prints_count_and_list(tmp_path):
    root = _init_repo_with_plan(tmp_path)
    r = _run(["python3", os.path.join(BIN, "echo-stage"), "checklist"], root)
    assert r.returncode == 0
    assert "checklist: 1/3 done" in r.stdout
    assert "1. [ ] 1. first step" in r.stdout
    assert "2. [x] 2. second step" in r.stdout


def test_cli_checklist_no_plan_fails_open(tmp_path):
    root = _init_repo(tmp_path)  # no plan artifact recorded
    r = _run(["python3", os.path.join(BIN, "echo-stage"), "checklist"], root)
    assert r.returncode == 0
    assert r.stdout.strip() == "checklist: none"


def test_cli_checklist_no_state_fails_open(tmp_path):
    root = str(tmp_path)  # no echo init at all
    r = _run(["python3", os.path.join(BIN, "echo-stage"), "checklist"], root)
    assert r.returncode == 0
    assert r.stdout.strip() == "checklist: none"


def test_cli_check_sets_marker_without_rewriting_text(tmp_path):
    root = _init_repo_with_plan(tmp_path)
    before = _plan_text(root)
    r = _run(["python3", os.path.join(BIN, "echo-stage"), "check", "--index", "1"], root)
    assert r.returncode == 0
    after = _plan_text(root)
    assert after == before.replace("- [ ] 1. first step", "- [x] 1. first step", 1)
    r2 = _run(["python3", os.path.join(BIN, "echo-stage"), "checklist"], root)
    assert "checklist: 2/3 done" in r2.stdout


def test_cli_uncheck_reverts(tmp_path):
    root = _init_repo_with_plan(tmp_path)
    _run(["python3", os.path.join(BIN, "echo-stage"), "check", "--index", "1"], root)
    r = _run(["python3", os.path.join(BIN, "echo-stage"), "uncheck", "--index", "1"], root)
    assert r.returncode == 0
    assert _plan_text(root) == _PLAN_FIXTURE


def test_cli_check_out_of_range_exits_2(tmp_path):
    root = _init_repo_with_plan(tmp_path)
    r = _run(["python3", os.path.join(BIN, "echo-stage"), "check", "--index", "9"], root)
    assert r.returncode == 2
    assert _plan_text(root) == _PLAN_FIXTURE  # unchanged


def test_cli_check_no_plan_exits_2(tmp_path):
    root = _init_repo(tmp_path)  # no plan artifact recorded
    r = _run(["python3", os.path.join(BIN, "echo-stage"), "check", "--index", "1"], root)
    assert r.returncode == 2


def test_cli_check_next_marks_first_unchecked(tmp_path):
    root = _init_repo_with_plan(tmp_path)
    r = _run(["python3", os.path.join(BIN, "echo-stage"), "check-next"], root)
    assert r.returncode == 0
    assert "checked: 1. 1. first step" in r.stdout
    assert "- [x] 1. first step" in _plan_text(root)


def test_cli_check_next_noop_when_all_checked(tmp_path):
    body = "## Order of work\n- [x] 1. only step\n"
    root = _init_repo_with_plan(tmp_path, body=body)
    r = _run(["python3", os.path.join(BIN, "echo-stage"), "check-next"], root)
    assert r.returncode == 0
    assert r.stdout.strip() == "checklist: nothing to check"


def test_cli_check_next_no_plan_fails_open(tmp_path):
    root = _init_repo(tmp_path)  # no plan artifact recorded
    r = _run(["python3", os.path.join(BIN, "echo-stage"), "check-next"], root)
    assert r.returncode == 0
    assert r.stdout.strip() == "checklist: nothing to check"


# ---- CLI: echo-watch fail-open run (no remote / no PR) ----

def test_watch_run_fail_open_no_pr(tmp_path):
    root = _init_repo(tmp_path)  # git repo, no remote, no PR
    r = _run(["python3", os.path.join(BIN, "echo-watch"), "run",
              "--ticket", "FEAT-3816"], root)
    assert r.returncode == 0
    art = os.path.join(root, ".echo", "verify", "FEAT-3816-ci.md")
    assert os.path.exists(art)
    with open(art, encoding="utf-8") as fh:
        body = fh.read()
    assert "result: skipped" in body
    assert "post " not in r.stdout  # no Jira event emitted on the fail-open path


def test_watch_gh_timeout_branch_fails_open(monkeypatch):
    # A hung gh call (simulated as TimeoutExpired) is treated as a gh failure:
    # _gh returns None and _gh_available returns False, never a traceback/hang.
    mod = _load_watch_module()

    def _raise_timeout(*a, **k):
        raise subprocess.TimeoutExpired(cmd="gh", timeout=k.get("timeout", 1))

    monkeypatch.setattr(mod.subprocess, "run", _raise_timeout)
    assert mod._gh(["pr", "view"], cwd=".") is None
    assert mod._gh_available() is False


def test_watch_run_fail_open_on_gh_timeout(tmp_path, monkeypatch):
    # The bounded `run` path must fail open (skipped artifact, exit 0) when gh
    # hangs, not block forever. Simulate a hung gh with no real network.
    root = _init_repo(tmp_path)
    mod = _load_watch_module()
    real_run = subprocess.run  # capture before patching the shared module

    def _raise_timeout(cmd, *a, **k):
        if cmd and cmd[0] == "gh":
            raise subprocess.TimeoutExpired(cmd=cmd, timeout=k.get("timeout", 1))
        return real_run(cmd, *a, **k)  # git and friends stay real

    monkeypatch.setattr(mod.subprocess, "run", _raise_timeout)

    class _Args:
        ticket = "FEAT-3816"
        author = None
        interval = 15
        max_wait = 120

    monkeypatch.chdir(root)
    try:
        mod.cmd_run(_Args())
        raised = None
    except SystemExit as exc:
        raised = exc.code
    assert raised == 0  # fail open, never a hang or crash
    art = os.path.join(root, ".echo", "verify", "FEAT-3816-ci.md")
    assert os.path.exists(art)
    with open(art, encoding="utf-8") as fh:
        assert "result: skipped" in fh.read()


def test_watch_run_rejects_bad_ticket(tmp_path):
    # An invalid or traversal ticket exits 2 and writes nothing outside verify/.
    root = _init_repo(tmp_path)
    for bad in ("../evil", "not-a-ticket"):
        r = _run(["python3", os.path.join(BIN, "echo-watch"), "run",
                  "--ticket", bad], root)
        assert r.returncode == 2
    # `../evil` would resolve to .echo/evil-ci.md (one level above verify/).
    assert not os.path.exists(os.path.join(root, ".echo", "evil-ci.md"))
    verify = os.path.join(root, ".echo", "verify")
    stray = os.listdir(verify) if os.path.isdir(verify) else []
    assert stray == []  # no artifact written for a rejected ticket


def test_watch_run_rejects_nonpositive_poll(tmp_path):
    # A 0/negative interval or max-wait is rejected so it cannot busy-loop.
    root = _init_repo(tmp_path)
    r = _run(["python3", os.path.join(BIN, "echo-watch"), "run",
              "--ticket", "FEAT-3816", "--interval", "0"], root)
    assert r.returncode == 2
    r2 = _run(["python3", os.path.join(BIN, "echo-watch"), "run",
               "--ticket", "FEAT-3816", "--max-wait", "-5"], root)
    assert r2.returncode == 2


# ---- CLI: mandatory watch gate at ship -> done ----

def _ship_ready(tmp_path):
    root = _init_repo(tmp_path)
    S = os.path.join(BIN, "echo-stage")
    _run(["python3", S, "set-stage", "--stage", "ship"], root)
    _run(["python3", S, "approve"], root)  # approve the ship gate
    return root, S


def test_watch_gate_blocks_without_artifact(tmp_path):
    root, S = _ship_ready(tmp_path)
    r = _run(["python3", S, "next"], root)
    assert r.returncode == 2  # no watch artifact -> blocked
    assert ec.load_state(root)["items"]["FEAT-3816"]["stage"] == "ship"  # did not advance


def test_watch_gate_allows_with_artifact(tmp_path):
    root, S = _ship_ready(tmp_path)
    art = ec.watch_artifact_path("FEAT-3816", root)
    os.makedirs(os.path.dirname(art), exist_ok=True)
    with open(art, "w", encoding="utf-8") as fh:
        fh.write("- result: pass\n")
    r = _run(["python3", S, "next"], root)
    assert r.returncode == 0
    assert "advanced:done" in r.stdout


def test_watch_gate_off_advances_without_artifact(tmp_path):
    root, S = _ship_ready(tmp_path)
    cfg = ec.load_config(root)
    cfg["watch_gate"] = "off"
    ec.save_config(cfg, root)
    r = _run(["python3", S, "next"], root)
    assert r.returncode == 0
    assert "advanced:done" in r.stdout


def test_watch_gate_fails_open_without_active_item(tmp_path):
    root = str(tmp_path)  # no echo state at all
    r = _run(["python3", os.path.join(BIN, "echo-stage"), "next"], root)
    assert r.returncode == 2  # blocked by the _require_state guard, never crashes


# ---- CLI: ledger re-alert with parameterized event keys ----

def test_ledger_realert_on_new_sha(tmp_path):
    root = _init_repo(tmp_path)  # FEAT-3816 active
    S = os.path.join(BIN, "echo-stage")
    _run(["python3", S, "comment-done", "--event", "ci:failed:sha1"], root)
    same = _run(["python3", S, "comment-needed", "--event", "ci:failed:sha1"], root)
    assert same.stdout.strip() == "skip"                 # same sha -> no re-post
    fresh = _run(["python3", S, "comment-needed", "--event", "ci:failed:sha2"], root)
    assert fresh.stdout.strip() == "post FEAT-3816"      # new sha -> re-alert


def test_ledger_realert_on_new_review_id(tmp_path):
    root = _init_repo(tmp_path)
    S = os.path.join(BIN, "echo-stage")
    _run(["python3", S, "comment-done", "--event", "review:seen:1001"], root)
    same = _run(["python3", S, "comment-needed", "--event", "review:seen:1001"], root)
    assert same.stdout.strip() == "skip"
    fresh = _run(["python3", S, "comment-needed", "--event", "review:seen:1002"], root)
    assert fresh.stdout.strip() == "post FEAT-3816"
