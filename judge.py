from collections import Counter
import json
import math
from operator import itemgetter
import os
from pathlib import Path
import sys
import tempfile
import time
from typing import Any, Optional, Tuple, Dict, Union
from dodona_command import Judgement, MessageFormat, Tab, Context, TestCase, Test, Annotation, Message, ErrorType
import subprocess
from helpers import tree

def get_test_output_files(test_source_path:Path, evaluation_folder:Path, build_path:Path) -> Dict[str, Path]:
    rel_path = test_source_path.relative_to(evaluation_folder)

    return {
        "stdout": build_path / "test" / rel_path.parent / "Output" / f"{test_source_path.name}.tmp.stdout",
        "stderr": build_path / "test" / rel_path.parent / "Output" / f"{test_source_path.name}.tmp.stderr"
    }

def warn_unexpected_error(error_message:str):
    lightning_icon = "&#9889;"

    warning = f"{lightning_icon} **Your solution threw an unexpected error:**\n```\n{error_message}\n```"

    warning = "\n".join(f"> {l}" for l in warning.split("\n"))

    with Message(
        description = warning,
        format = MessageFormat.MARKDOWN,
    ):
        return
    
def warn_timeout(duration:float):
    stopwatch_icon = "&#9201;&#65039;"

    warning = f"{stopwatch_icon} **Your solution timed out:** it took more than {duration:.1f} s"

    warning = "\n".join(f"> {l}" for l in warning.split("\n"))

    with Message(
        description = warning,
        format = MessageFormat.MARKDOWN,
    ):
        return

def _test_run_helper(test_source_path:Path, expected_output_path:Path, expected_error_path:Path, evaluation_folder:Path, build_path:Path) -> Dict[str, Any]:
    if expected_output_path.exists():
        with expected_output_path.open("r", errors="replace") as f:
            expected_output = f.read()
    else:
        expected_output = ""
    
    if expected_error_path.exists():
        with expected_error_path.open("r", errors="replace") as f:
            expected_error = f.read()
    else:
        expected_error = ""

    lit_target_path = build_path / "test" / (test_source_path.relative_to(evaluation_folder))
    try:
        tmp_lit_ouput_file = tempfile.NamedTemporaryFile(delete=False)

        proc_rec = subprocess.run(["lit", str(lit_target_path), "-o", tmp_lit_ouput_file.name], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        with open(tmp_lit_ouput_file.name, "r") as f:
            lit_output_json = json.load(f)["tests"][0]
    finally:
        os.remove(tmp_lit_ouput_file.name)

    is_correct = (proc_rec.returncode == 0)
    test_status = lit_output_json["code"] # "PASS" -> is_correct == True, "TIMEOUT" or "FAIL" -> is_correct = False
    test_duration = lit_output_json["elapsed"]

    if lit_target_path.name.endswith(".custom.c"):
        expected_output = None
        return {
            "correct":          is_correct,
            "status":           test_status,
            "duration":         test_duration,
            "expected_output":  expected_output,
            "expected_error":   None,
            "generated_output": None,
            "generated_error":  None,
        }
    else:
        stdout_file_path, stderr_file_path = itemgetter("stdout", "stderr")(get_test_output_files(test_source_path, evaluation_folder, build_path))

        with stdout_file_path.open("r", errors="replace") as f:
            generated_output = f.read()
        with stderr_file_path.open("r", errors="replace") as f:
            generated_error  = f.read()
    
        return {
            "correct":          is_correct,
            "status":           test_status,
            "duration":         test_duration,
            "expected_output":  expected_output,
            "expected_error":   expected_error,
            "generated_output": generated_output,
            "generated_error":  generated_error,
        }

_status_correct = {
    "enum": ErrorType.CORRECT, 
    "human": ErrorType.CORRECT, # "correct" is readable enough for humans
}

_status_wrong = {
    "enum": ErrorType.WRONG, 
    "human": ErrorType.WRONG, # "wrong" is readable enough for humans
}

def run_test(test_source_path:Path, expected_output_path:Path, expected_error_path:Path, evaluation_folder:Path, build_path:Path) -> Counter:
    (
        is_correct,
        test_status,
        test_duration,
        expected_output,
        expected_error,
        generated_output,
        generated_error,
    ) = itemgetter(
        "correct",
        "status",
        "duration",
        "expected_output",
        "expected_error",
        "generated_output",
        "generated_error"
    )(_test_run_helper(test_source_path, expected_output_path, expected_error_path, evaluation_folder=evaluation_folder, build_path=build_path))

    is_custom_test = test_source_path.name.endswith(".custom.c")
    did_timeout = (test_status == "TIMEOUT")

    # --- Test file to markdown ---
    with test_source_path.open("r", encoding="utf-8") as f:
        short_file_path_str = str(test_source_path.relative_to(evaluation_folder))

        test_code = f.readlines()

        if len(test_code) > 10:
            # do not show more than 10 lines of code
            test_code = test_code[:9] + ["... // Remainder of code omitted"]
        
        test_code = "".join(test_code)

        test_code_md = f"```c\n{test_code}\n```"
    
    if False: #is_custom_test:
        with Test(description={"description": f" &#x1F4C4; {short_file_path_str}\n{test_code_md}", "format": MessageFormat.MARKDOWN}, expected="") as test:
            if is_correct:
                test.status = _status_correct
            else:
                test.status = _status_wrong
            test.generated = ""

            if did_timeout:
                warn_timeout(test_duration)
    else:
        # --- Get expected output/error ---

        if expected_error:
            expected = expected_error
            generated = generated_error
            unexpected_error = False
        else:
            expected = expected_output
            generated = generated_output
            
            unexpected_error = bool(generated_error)
        
        # --- Output test info ---

        with Test(description={"description": f" &#x1F4C4; {short_file_path_str}\n{test_code_md}", "format": MessageFormat.MARKDOWN}, expected=expected) as test:
            if is_correct:
                test.status = _status_correct
            else:
                test.status = _status_wrong
            test.generated = generated

            if unexpected_error:
                warn_unexpected_error(generated_error)
            elif did_timeout:
                warn_timeout(test_duration)
    
    # --- Help counting the total number of (in)correct tests

    return Counter({
        "correct": int(is_correct),
        "total": 1
    })

def success_bar(num_success:int, num_total:int, width:int=20):
    success_rate = num_success/num_total
    bar_length = math.floor(success_rate*width)

    return "\u2588"*bar_length + "\u2591"*(width - bar_length)

def run_hidden_tests(hidden_tests_folder:Path, evaluation_folder:Path, build_path:Path) -> Counter:
    all_source_files = [f for f in hidden_tests_folder.glob("**/*.c")]

    num_success = 0
    num_tests = 0

    for test_source_path in all_source_files:
        expected_output_path = hidden_tests_folder / f"{test_source_path.name}.stdout"
        expected_error_path = hidden_tests_folder / f"{test_source_path.name}.stderr"

        is_correct = _test_run_helper(test_source_path, expected_output_path, expected_error_path, evaluation_folder=evaluation_folder, build_path=build_path)["correct"]

        num_success += is_correct
        num_tests += 1

    test_case_message = {"description": f"##### Hidden tests: {success_bar(num_success, num_tests)} {num_success}/{num_tests} correct", "format": MessageFormat.MARKDOWN}

    with TestCase(test_case_message) as test_case:
        test_case.accepted = (num_success == num_tests)
        pass

    return Counter({
        "correct": num_success,
        "total": num_tests
    })

def folder_path_to_title(folder_path:Path) -> str:
    return folder_path.name.replace("_", " ").replace("-", " ").capitalize()

def run_test_case(test_case_folder_path:Path, evaluation_folder:Path, build_path:Path, is_dummy:bool=False) -> Counter:
    res = Counter()

    test_case_name = {"description": f"##### {folder_path_to_title(test_case_folder_path)}", "format": MessageFormat.MARKDOWN}

    with TestCase(test_case_name) as test_case:
        all_source_files = test_case_folder_path.glob("*.c")

        for test_source_path in all_source_files:

            expected_output_path = test_case_folder_path / f"{test_source_path.name}.stdout"
            expected_error_path = test_case_folder_path / f"{test_source_path.name}.stderr"

            res += run_test(test_source_path, expected_output_path, expected_error_path, evaluation_folder=evaluation_folder, build_path=build_path)
    
    return res

def test_submission(evaluation_folder:Path, build_path:Path) -> Counter:
    # evaluation_folder is the "evaluation" folder in the course repo

    res = Counter()

    # Tabs correspond to top-level rubrics (e.g. "Literals")
    tab_folders = [item for item in evaluation_folder.glob("*") if item.is_dir()]
    for folder in tab_folders:
        res += create_tab(folder, evaluation_folder=evaluation_folder, build_path=build_path)

    return res

def create_tab(tab_folder:Path, evaluation_folder:Path, build_path:Path) -> Counter:
    # A tab corresponds to a top-level rubric, like "Literals"
    # A tab might have one or more contexts, which correspond to sub-rubrics 
    # (like "Numeric literals", "String literals" or "Error-handling").
    # If there are no sub-rubrics, then a dummy-context is created to hold all
    # testcases for this tab

    is_grading_only = (set(tab_folder.glob("**/*.c")) == set(tab_folder.glob("grading/**/*.c")))

    if is_grading_only:
        return Counter()

    # If there are sub_rubrics then the tab_folder contains a folder for each 
    # sub-rubric, which contain folders for all test cases, which each contain
    # c files for each test
    has_sub_rubrics = bool(list(tab_folder.glob("*/**/*.c"))) and not all(f.name in ("hidden", "grading") for f in tab_folder.iterdir() if f.is_dir())

    res = Counter()

    with Tab(title=folder_path_to_title(tab_folder)) as tab:
        if not has_sub_rubrics:
            res += create_context(tab_folder, evaluation_folder=evaluation_folder, build_path=build_path, is_dummy=True) # dummy context
        else:
            context_folders = [item for item in tab_folder.glob("*") if item.is_dir()]
            for folder in context_folders:
                res += create_context(folder, evaluation_folder=evaluation_folder, build_path=build_path)
        
        num_incorrect = res["total"] - res["correct"]
        tab.badgeCount = num_incorrect
    
    return res

def create_context(context_folder:Path, evaluation_folder:Path, build_path:Path, is_dummy:bool=False) -> Counter:
    res = Counter()

    if not is_dummy:
        context_name = folder_path_to_title(context_folder)
        ctx_kwargs = {
            "description":{
                "description": f"#### {context_name}",
                "format": MessageFormat.MARKDOWN
            }
        }
    else:
        ctx_kwargs = {}

    has_sub_folders = bool(list(context_folder.glob("*/**/*.c"))) and not all(f.name == "hidden" for f in context_folder.iterdir() if f.is_dir())

    with Context(**ctx_kwargs) as ctx:
        if not has_sub_folders:
            res += run_test_case(context_folder, evaluation_folder=evaluation_folder, build_path=build_path)
            if (context_folder / "hidden").exists():
                res += run_hidden_tests(context_folder / "hidden", evaluation_folder=evaluation_folder, build_path=build_path)
        else:
            test_case_folders = [item for item in context_folder.glob("*") if item.is_dir()]
            
            for folder in test_case_folders:
                if folder.name in ("hidden", "grading"):
                    continue # We want to run the hidden tests last
                else:
                    res += run_test_case(folder, evaluation_folder=evaluation_folder, build_path=build_path)
            
            if (context_folder / "hidden").exists():
                res += run_hidden_tests(context_folder / "hidden", evaluation_folder=evaluation_folder, build_path=build_path)
    
    return res