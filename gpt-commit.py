#!/usr/bin/env python3

import os
import openai
import subprocess

DIFF_PROMPT = "Generate a succinct summary of the following code changes:"
COMMIT_MSG_PROMPT = "Generate a short commit message from this:"
openai.organization = os.getenv("OPENAI_ORG_ID")
openai.api_key = os.environ["OPENAI_API_KEY"]


def complete(prompt):
    completion_resp = openai.Completion.create(prompt=prompt[:10000],
                                               engine="text-davinci-003",
                                               max_tokens=128)
    completion = completion_resp["choices"][0]["text"].strip()
    return completion


def summarize_diff(diff):
    assert diff
    return complete(DIFF_PROMPT + "\n\n" + diff + "\n\n")


def generate_commit_message(summaries):
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


def commit(message):
    return subprocess.run(["git", "commit", "--message", message,
                           "--edit"]).returncode


if __name__ == "__main__":
    diff = get_diff()
    if not diff:
        # no files staged or only whitespace diffs
        commit_message = "Fix whitespace"
    elif len(diff) < 9900:
        commit_message = generate_commit_message(summarize_diff(diff))
    else:
        summaries = summarize_added_modified() + "\n\n" + summarize_deleted(
        ) + "\n\n" + summarize_other()
        commit_message = generate_commit_message(summaries)
    exit(commit(commit_message))
