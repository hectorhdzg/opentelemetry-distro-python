#!/usr/bin/env python

# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

"""Run mypy against the target package."""

import argparse
import logging
import os
import sys
from subprocess import CalledProcessError, check_call

logging.getLogger().setLevel(logging.INFO)

PYTHON_VERSION = "3.10"

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run mypy against target folder.")
    parser.add_argument(
        "-t",
        "--target",
        dest="target_package",
        help="The target package directory on disk.",
        required=True,
    )
    args = parser.parse_args()

    package_dir = os.path.abspath(args.target_package)
    src_dir = os.path.join(package_dir, "src")

    commands = [
        sys.executable,
        "-m",
        "mypy",
        "--python-version",
        PYTHON_VERSION,
        "--show-error-codes",
        "--ignore-missing-imports",
    ]

    # Check source code
    src_code = [*commands, src_dir]
    src_code_error = None
    try:
        logging.info("Running mypy on src: %s", src_code)
        check_call(src_code)
    except CalledProcessError as e:
        src_code_error = e

    # Check samples if they exist
    sample_code_error = None
    samples_dir = os.path.join(package_dir, "samples")
    if os.path.exists(samples_dir):
        sample_code = [
            *commands,
            "--check-untyped-defs",
            "--follow-imports=silent",
            samples_dir,
        ]
        try:
            logging.info("Running mypy on samples: %s", sample_code)
            check_call(sample_code)
        except CalledProcessError as e:
            sample_code_error = e

    # Check tests if they exist
    test_code_error = None
    tests_dir = os.path.join(package_dir, "tests")
    if os.path.exists(tests_dir):
        test_code = [
            *commands,
            "--check-untyped-defs",
            "--follow-imports=silent",
            tests_dir,
        ]
        try:
            logging.info("Running mypy on tests: %s", test_code)
            check_call(test_code)
        except CalledProcessError as e:
            test_code_error = e

    if src_code_error or sample_code_error or test_code_error:
        if src_code_error:
            logging.error("mypy failed on src code: %s", src_code_error)
        if sample_code_error:
            logging.error("mypy failed on sample code: %s", sample_code_error)
        if test_code_error:
            logging.error("mypy failed on test code: %s", test_code_error)
        sys.exit(1)
