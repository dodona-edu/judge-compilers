import re
from typing import Optional

from dodona_command import Annotation, Message, MessageFormat

_is_undefined_reference = r"\/usr\/bin\/ld: .*\n?\w+\.(?:h|cpp):\([\w\+\.]+\): undefined reference to `(?P<missing_reference>[^']*)'"
_is_compile_error = r"[\/\w\.]+:(?P<line>\d+):(?P<column>\d+): error: (?P<message>.+)"

def handle_compile_error(stderr_content:str, exit_code:Optional[int]=None):
    """
    Handles compile errors and link time errors on undefined references
    """

    undefined_references = list(re.finditer(_is_undefined_reference, stderr_content, flags=re.MULTILINE))

    if undefined_references:
        missing_references = set(m.group("missing_reference") for m in undefined_references)

        with Message(
            description = "Could not find the following references:\n" + "\n".join([f" * `{m_ref}`" for m_ref in missing_references]),
            format = MessageFormat.MARKDOWN,
            type="error"
        ):
            return
    else:
        compile_error_match = re.search(_is_compile_error, stderr_content, flags=re.MULTILINE)

        if compile_error_match:
            line = compile_error_match.group("line")
            column = compile_error_match.group("column")
            error_message = compile_error_match.group("message")

            with Message(
                description = error_message, format=MessageFormat.CODE
            ):
                with Annotation(
                    row = int(line),
                    text = error_message,
                    type="error"
                ):
                    return
    
    error_message_md = "> ```\n" + ("\n".join(
        "> " + line
            for line in stderr_content.split("\n")
    )) + "\n> ```"

    with Message(
        description = f"Failed to build solution.\nCmake returned exit code **{exit_code}**.\n{error_message_md}",
        format = MessageFormat.MARKDOWN,
        type="error"
    ):
        return