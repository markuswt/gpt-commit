#!/usr/bin/env python3

import argparse
import asyncio
import os
import subprocess
import sys

import openai

DIFF_PROMPT = "Generate a succinct summary of the following code changes:"
COMMIT_MSG_PROMPT = (
    "Using no more than 50 characters, "
    "generate a descriptive commit message from these summaries:"
)
PROMPT_CUTOFF = 10000
openai.organization = os.getenv("OPENAI_ORG_ID")
openai.api_key = os.environ["OPENAI_API_KEY"]


def get_diff(ignore_whitespace=True):
    arguments = [
        "git",
        "--no-pager",
        "diff",
        "--staged",
    ]
    if ignore_whitespace:
        arguments += [
            "--ignore-space-change",
            "--ignore-blank-lines",
        ]
    diff_process = subprocess.run(arguments, capture_output=True, text=True)
    diff_process.check_returncode()
    return diff_process.stdout.strip()


def parse_diff(diff):
    file_diffs = diff.split("\ndiff")
    file_diffs = [file_diffs[0]] + [
        "\ndiff" + file_diff for file_diff in file_diffs[1:]
    ]
    chunked_file_diffs = []
    for file_diff in file_diffs:
        [head, *chunks] = file_diff.split("\n@@")
        chunks = ["\n@@" + chunk for chunk in reversed(chunks)]
        chunked_file_diffs.append((head, chunks))
    return chunked_file_diffs


def assemble_diffs(parsed_diffs, cutoff):
    """
    Create multiple well-formatted diff strings, each being shorter than cutoff
    """
    assembled_diffs = [""]

    def add_chunk(chunk):
        if len(assembled_diffs[-1]) + len(chunk) <= cutoff:
            assembled_diffs[-1] += "\n" + chunk
            return True
        else:
            assembled_diffs.append(chunk)
            return False

    for head, chunks in parsed_diffs:
        if not chunks:
            add_chunk(head)
        else:
            add_chunk(head + chunks.pop())
        while chunks:
            if not add_chunk(chunks.pop()):
                assembled_diffs[-1] = head + assembled_diffs[-1]
    return assembled_diffs


async def complete(prompt):
    completion_resp = await openai.ChatCompletion.acreate(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt[: PROMPT_CUTOFF + 100]}],
        max_tokens=128,
    )
    completion = completion_resp.choices[0].message.content.strip()
    return completion


async def summarize_diff(diff):
    assert diff
    return await complete(DIFF_PROMPT + "\n\n" + diff + "\n\n")


async def summarize_summaries(summaries):
    assert summaries
    return await complete(COMMIT_MSG_PROMPT + "\n\n" + summaries + "\n\n")


async def generate_commit_message(diff):
    if not diff:
        return "Fix whitespace"

    assembled_diffs = assemble_diffs(parse_diff(diff), PROMPT_CUTOFF)
    summaries = await asyncio.gather(
        *[summarize_diff(diff) for diff in assembled_diffs]
    )
    return await summarize_summaries("\n".join(summaries))


def commit(message):
    # will ignore message if diff is empty
    return subprocess.run(["git", "commit", "--message", message, "--edit"]).returncode


def parse_args():
    """
    Extract the CLI arguments from argparse
    """
    parser = argparse.ArgumentParser(
        description=(
            "Generate a commit message for staged files and commit them. "
            "Git will prompt you to edit the generated commit message."
        )
    )
    parser.add_argument(
        "-p",
        "--print-message",
        action="store_true",
        default=False,
        help="print message in place of performing commit",
    )
    return parser.parse_args()


async def main():
    args = parse_args()

    try:
        if not get_diff(ignore_whitespace=False):
            print(
                "No changes staged. Use `git add` to stage files before invoking gpt-commit."
            )
            exit()
        commit_message = await generate_commit_message(get_diff())
    except UnicodeDecodeError:
        print("gpt-commit does not support binary files", file=sys.stderr)
        commit_message = (
            "# gpt-commit does not support binary files. "
            "Please enter a commit message manually or unstage any binary files."
        )

    if args.print_message:
        print(commit_message)
    else:
        exit(commit(commit_message))


if __name__ == "__main__":
    asyncio.run(main())
