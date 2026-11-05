import json

import pytest

from dodona_command import Annotation, Context, ErrorType, Judgement, Message, MessageFormat, Tab, Test, TestCase


def test_str_returns_value() -> None:
    assert str(ErrorType.WRONG) == "wrong"
    assert str(MessageFormat.MARKDOWN) == "markdown"


def test_format_and_json_use_value() -> None:
    assert f"{ErrorType.COMPILATION_ERROR}" == "compilation error"
    assert json.dumps({"enum": ErrorType.WRONG, "format": MessageFormat.CODE}) == '{"enum": "wrong", "format": "code"}'


def printed_commands(capsys: pytest.CaptureFixture[str]) -> list[dict]:
    decoder = json.JSONDecoder()
    out = capsys.readouterr().out
    commands, pos = [], 0
    while pos < len(out):
        if out[pos].isspace():
            pos += 1
            continue
        command, pos = decoder.raw_decode(out, pos)
        commands.append(command)
    return commands


def test_nested_commands_print_start_and_close(capsys: pytest.CaptureFixture[str]) -> None:
    with Judgement() as judgement:
        with Tab(title="tab") as tab:
            with Context(description="context") as context:
                with TestCase({"format": MessageFormat.MARKDOWN, "description": "case"}) as test_case:
                    with Test(description="test", expected="1") as test:
                        with Message(format=MessageFormat.CODE, description="msg", type="error"):
                            pass
                        with Annotation(row=3, text="note", type="error"):
                            pass
                        test.status = {"enum": ErrorType.WRONG, "human": ErrorType.WRONG}
                        test.generated = "2"
                    test_case.accepted = False
                context.accepted = False
            tab.badgeCount = 1
        judgement.status = {"enum": ErrorType.COMPILATION_ERROR, "human": ErrorType.COMPILATION_ERROR}
        judgement.accepted = False

    assert printed_commands(capsys) == [
        {"command": "start-judgement"},
        {"command": "start-tab", "title": "tab"},
        {"command": "start-context", "description": "context"},
        {"command": "start-testcase", "description": {"format": "markdown", "description": "case"}},
        {"command": "start-test", "description": "test", "expected": "1"},
        {"command": "append-message", "message": {"format": "code", "description": "msg", "type": "error"}},
        {"command": "annotate-code", "row": 3, "text": "note", "type": "error"},
        {
            "command": "close-test",
            "status": {"enum": "wrong", "human": "wrong"},
            "generated": "2",
        },
        {"command": "close-testcase", "accepted": False},
        {"command": "close-context", "accepted": False},
        {"command": "close-tab", "badgeCount": 1},
        {
            "command": "close-judgement",
            "status": {"enum": "compilation error", "human": "compilation error"},
            "accepted": False,
        },
    ]


def fail_in_judgement() -> None:
    with Judgement():
        msg = "boom"
        raise ValueError(msg)


def test_exception_propagates_and_close_is_printed(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(ValueError, match="boom"):
        fail_in_judgement()

    assert printed_commands(capsys) == [{"command": "start-judgement"}, {"command": "close-judgement"}]
