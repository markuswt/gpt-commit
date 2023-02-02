#!/usr/bin/env python3

import openai
import os
import subprocess
import sys

DIFF_PROMPT = "Generate a succinct summary of the following code changes:"
COMMIT_MSG_PROMPT = "Generate a short commit message from this:"
PROMPT_CUTOFF = 10000
openai.organization = os.getenv("OPENAI_ORG_ID")
openai.api_key = os.environ["OPENAI_API_KEY"]


def complete(prompt):
    completion_resp = openai.Completion.create(prompt=prompt[:PROMPT_CUTOFF],
                                               engine="text-davinci-003",
                                               max_tokens=128)
    completion = completion_resp["choices"][0]["text"].strip()
    return completion


def summarize_diff(diff):
    assert diff
    return complete(DIFF_PROMPT + "\n\n" + diff + "\n\n")


def summarize_summaries(summaries):
    assert summaries
    return complete(COMMIT_MSG_PROMPT + "\n\n" + summaries + "\n\n")


def get_diff(path=".", diff_filter="ACDMRTUXB", name_only=False):
    arguments = [
        "git", "--no-pager", "diff", "--staged", "--ignore-space-change",
        "--ignore-all-space", "--ignore-blank-lines",
        f"--diff-filter={diff_filter}"
    ]
    if name_only:
        arguments.append("--name-only")
    
    diff_process = subprocess.run(arguments + [path],
                                  capture_output=True,
                                  text=True)
    diff_process.check_returncode()
    return diff_process.stdout.strip()


def summarize_added_modified():
    modified_files = get_diff(name_only=True, diff_filter="AM").splitlines()
    return "\n\n".join(
        [summarize_diff(get_diff(file)) for file in modified_files])


def summarize_deleted():
    deleted_files = get_diff(name_only=True, diff_filter="D").splitlines()
    return f"This change deletes files {', '.join(deleted_files)}" if deleted_files else ""


def summarize_other():
    other_changes = get_diff(diff_filter="CRTUXB")
    return summarize_diff(other_changes) if other_changes else ""


def generate_commit_message(diff):
    if not diff:
        # no files staged or only whitespace diffs
        return "Fix whitespace"
    elif len(diff) < PROMPT_CUTOFF - len(DIFF_PROMPT) // 3:
        return summarize_summaries(summarize_diff(diff))
    
    # diff too large, split it up in chunks to summarize
    summaries = summarize_added_modified() + "\n\n" + summarize_deleted(
    ) + "\n\n" + summarize_other()
    return summarize_summaries(summaries)


def commit(message):
    # will ignore message if diff is empty
    return subprocess.run(["git", "commit", "--message", message,
                           "--edit"]).returncode


if __name__ == "__main__":
    try:
        diff = get_diff()
        commit_message = generate_commit_message(diff)
    except UnicodeDecodeError:
        print("gpt-commit does not support binary files", file=sys.stderr)
        commit_message = "# gpt-commit does not support binary files. Please enter a commit message manually or unstage any binary files."
    
    if "--print-message" in sys.argv:
        print(commit_message)
    else:
        exit(commit(commit_message))
