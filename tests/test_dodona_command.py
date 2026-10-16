import json

from dodona_command import ErrorType, MessageFormat


def test_str_returns_value() -> None:
    assert str(ErrorType.WRONG) == "wrong"
    assert str(MessageFormat.MARKDOWN) == "markdown"


def test_format_and_json_use_value() -> None:
    assert f"{ErrorType.COMPILATION_ERROR}" == "compilation error"
    assert json.dumps({"enum": ErrorType.WRONG, "format": MessageFormat.CODE}) == '{"enum": "wrong", "format": "code"}'
