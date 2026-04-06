#!/usr/bin/env python

# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

"""Run pylint against the target package."""

import argparse
import logging
import os
import sys
from subprocess import CalledProcessError, check_call

logging.getLogger().setLevel(logging.INFO)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run pylint against target folder.")
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

    # Use pyproject.toml pylint config (picked up automatically)
    commands = [
        sys.executable,
        "-m",
        "pylint",
        "--output-format=parseable",
    ]

    exit_code = 0

    # Lint source code
    try:
        src_cmd = [*commands, src_dir]
        logging.info("Running pylint on src: %s", src_cmd)
        check_call(src_cmd)
    except CalledProcessError as e:
        logging.error("pylint failed on src code with exit code %s", e.returncode)
        exit_code = max(exit_code, e.returncode)

    # Lint tests if they exist
    tests_dir = os.path.join(package_dir, "tests")
    if os.path.exists(tests_dir):
        try:
            tests_cmd = [*commands, tests_dir]
            logging.info("Running pylint on tests: %s", tests_cmd)
            check_call(tests_cmd)
        except CalledProcessError as e:
            logging.error("pylint failed on tests with exit code %s", e.returncode)
            exit_code = max(exit_code, e.returncode)

    # Lint samples if they exist (disable import-error since samples have their own dependencies)
    samples_dir = os.path.join(package_dir, "samples")
    if os.path.exists(samples_dir):
        try:
            samples_cmd = [*commands, "--disable=import-error", samples_dir]
            logging.info("Running pylint on samples: %s", samples_cmd)
            check_call(samples_cmd)
        except CalledProcessError as e:
            logging.error("pylint failed on samples with exit code %s", e.returncode)
            exit_code = max(exit_code, e.returncode)
    sys.exit(exit_code)
