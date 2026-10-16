import json
import shutil
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"

# Tests using hexadecimal literals, keyed by path in evaluation/.
HEX_TESTS = {"hex/lower.c", "hex/mixed.c"}
# Tests with no .stdout file whose RUN line checks the driver's output itself.
CUSTOM_TESTS = {"custom/decimal.custom.c", "custom/hex.custom.c"}
VISIBLE_TESTS = {"decimal/single.c", "decimal/sum.c"} | HEX_TESTS | CUSTOM_TESTS
# Tests the wrong submission (no hexadecimal literals) must fail.
WRONG_TESTS = HEX_TESTS | {"custom/hex.custom.c"}


def parse_commands(stdout: str) -> list[dict]:
    # The judge prints indented JSON objects back to back, not one per line.
    decoder = json.JSONDecoder()
    commands, pos = [], 0
    while pos < len(stdout):
        if stdout[pos].isspace():
            pos += 1
            continue
        command, pos = decoder.raw_decode(stdout, pos)
        commands.append(command)
    return commands


def run_judge(tmp_path: Path, submission: str, evaluation: str = "evaluation") -> list[dict]:
    workdir = tmp_path / "workdir"
    shutil.copytree(FIXTURES / "workdir", workdir)
    request = {
        "resources": str(FIXTURES / evaluation),
        "source": str(FIXTURES / "submissions" / submission),
        "workdir": str(workdir),
        "memory_limit": 536870912,
        "time_limit": 60,
        "programming_language": "c",
        "natural_language": "en",
        "judge": str(REPO),
    }
    proc = subprocess.run(
        [str(REPO / "run")],
        input=json.dumps(request),
        capture_output=True,
        text=True,
        cwd=tmp_path,
        timeout=600,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    return parse_commands(proc.stdout)


def judgement(commands: list[dict]) -> dict:
    closes = [c for c in commands if c["command"] == "close-judgement"]
    assert len(closes) == 1
    return closes[0]


def statuses_by_test(commands: list[dict]) -> dict[str, str]:
    """Test status per path in evaluation/, from each start-test and its close-test."""
    results = {}
    last_description = None
    for command in commands:
        if command["command"] == "start-test":
            last_description = command["description"]["description"]
        elif command["command"] == "close-test":
            assert last_description is not None
            path = next(p for p in VISIBLE_TESTS if p in last_description)
            results[path] = command["status"]["enum"]
    return results


def custom_test_details(commands: list[dict]) -> dict[str, dict]:
    """Expected/generated output and message texts of each custom test, keyed by path in evaluation/."""
    details = {}
    current = None
    for command in commands:
        if command["command"] == "start-test":
            current = next((p for p in CUSTOM_TESTS if p in command["description"]["description"]), None)
            if current is not None:
                details[current] = {"expected": command["expected"], "generated": None, "messages": []}
        elif command["command"] == "append-message" and current is not None:
            details[current]["messages"].append(command["message"]["description"])
        elif command["command"] == "close-test":
            if current is not None:
                details[current]["generated"] = command.get("generated")
            current = None
    return details


def assert_custom_tests_have_no_output(commands: list[dict]) -> None:
    details = custom_test_details(commands)
    assert set(details) == CUSTOM_TESTS
    for path, detail in details.items():
        assert not detail["expected"], path
        assert not detail["generated"], path
        assert not any("No result was produced" in m for m in detail["messages"]), path


def hidden_accepted(commands: list[dict]) -> list[bool]:
    """accepted of each hidden-tests testcase, in judge order."""
    accepted = []
    expecting = False
    for command in commands:
        if command["command"] == "start-testcase":
            expecting = "Hidden tests" in command["description"]["description"]
        elif command["command"] == "close-testcase" and expecting:
            accepted.append(command["accepted"])
    return accepted


def test_correct_submission(tmp_path: Path) -> None:
    commands = run_judge(tmp_path, "correct.cpp")

    assert judgement(commands).get("accepted", True) is True
    assert statuses_by_test(commands) == dict.fromkeys(VISIBLE_TESTS, "correct")
    assert hidden_accepted(commands) == [True, True]
    assert_custom_tests_have_no_output(commands)


def test_wrong_submission(tmp_path: Path) -> None:
    commands = run_judge(tmp_path, "wrong.cpp")

    final = judgement(commands)
    assert final["accepted"] is False
    assert final["status"]["enum"] == "wrong"
    assert statuses_by_test(commands) == {path: "wrong" if path in WRONG_TESTS else "correct" for path in VISIBLE_TESTS}
    assert sorted(hidden_accepted(commands)) == [False, True]
    assert_custom_tests_have_no_output(commands)


def test_compile_error(tmp_path: Path) -> None:
    commands = run_judge(tmp_path, "compile_error.cpp")

    final = judgement(commands)
    assert final["accepted"] is False
    assert final["status"]["enum"] == "compilation error"
    assert not any(c["command"] == "start-test" for c in commands)
    assert any(c["command"] == "append-message" for c in commands)


# Folders in evaluation_no_result/ whose test is one lit cannot produce stdout/stderr files for.
NO_RESULT_TESTS = {"unrunnable", "no_run_line", "unsupported", "no_capture", "undiscovered"}


def test_no_lit_result(tmp_path: Path) -> None:
    commands = run_judge(tmp_path, "correct.cpp", evaluation="evaluation_no_result")

    final = judgement(commands)
    assert final["accepted"] is False
    assert final["status"]["enum"] == "wrong"

    results = {}
    current = None
    for command in commands:
        if command["command"] == "start-test":
            current = next(name for name in NO_RESULT_TESTS if f"{name}/a.c" in command["description"]["description"])
            results[current] = {"messages": []}
        elif command["command"] == "append-message" and current is not None:
            results[current]["messages"].append(command["message"]["description"])
        elif command["command"] == "close-test":
            results[current]["status"] = command["status"]["enum"]
            current = None

    assert set(results) == NO_RESULT_TESTS
    for name, result in results.items():
        assert result["status"] == "wrong", name
        assert len(result["messages"]) == 1, name
    assert "command not found" in results["unrunnable"]["messages"][0]
    assert "no 'RUN:' line" in results["no_run_line"]["messages"][0]
    assert "does not support" in results["unsupported"]["messages"][0]
    assert "did not discover any tests" in results["undiscovered"]["messages"][0]
