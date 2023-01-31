#!/usr/bin/env python3

import os
import requests
import subprocess

DIFF_PROMPT = "Generate a succinct summary of the following code changes:"
COMMIT_MSG_PROMPT = "Generate a short commit message from this:"
OPENAI_API_URL = "https://api.openai.com/v1/completions"
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
OPENAI_ORG_ID = os.getenv("OPENAI_ORG_ID")


def complete(prompt):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }
    if OPENAI_ORG_ID:
        headers["OpenAI-Organization"] = OPENAI_ORG_ID
    
    body = {
        "model": "text-davinci-003",
        "max_tokens": 64,
        "prompt": prompt[:12000]  # hard cutoff
    }
    response = requests.post(OPENAI_API_URL, headers=headers, json=body)
    response.raise_for_status()
    completion = response.json()["choices"][0]["text"].strip()
    return completion


def summarize_diff(diff):
    assert diff
    return complete(DIFF_PROMPT + "\n\n" + diff + "\n\n")


def generate_commit_message(summaries):
    assert summaries
    return complete(COMMIT_MSG_PROMPT + "\n\n" + summaries + "\n\n")


def get_diff(path=".", diff_filter="ACDMRTUXB", name_only=False):
    arguments = [
        "git", "--no-pager", "diff", "--staged", f"--diff-filter={diff_filter}"
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
    subprocess.run(["git", "commit", "--message", message,
                    "--edit"]).check_returncode()


if __name__ == "__main__":
    diff = get_diff()
    if not diff:
        print("Nothing to commit")
    elif len(diff) < 11900:
        commit_message = generate_commit_message(summarize_diff(diff))
        commit(commit_message)
    else:
        summaries = summarize_added_modified() + "\n\n" + summarize_deleted(
        ) + "\n\n" + summarize_other()
        commit_message = generate_commit_message(summaries)
        commit(commit_message)
