#!/usr/bin/env python3

import openai
import os
import subprocess
import sys

DIFF_PROMPT = "Generate a succinct summary of the following code changes:"
COMMIT_MSG_PROMPT = "Using no more than 50 characters, generate a descriptive commit message from these summaries:"
PROMPT_CUTOFF = 10000
openai.organization = os.getenv("OPENAI_ORG_ID")
openai.api_key = os.environ["OPENAI_API_KEY"]


def complete(prompt):
    completion_resp = openai.ChatCompletion.create(model="gpt-3.5-turbo",
                                                   messages=[{
                                                       "role":
                                                       "user",
                                                       "content":
                                                       prompt[:PROMPT_CUTOFF +
                                                              100]
                                                   }],
                                                   max_tokens=128)
    completion = completion_resp.choices[0].message.content.strip()
    return completion


def get_diff():
    arguments = [
        "git", "--no-pager", "diff", "--staged", "--ignore-space-change",
        "--ignore-all-space", "--ignore-blank-lines"
    ]
    diff_process = subprocess.run(arguments, capture_output=True, text=True)
    diff_process.check_returncode()
    return diff_process.stdout.strip()


def parse_diff(diff):
    file_diffs = diff.split("\ndiff")
    file_diffs = [file_diffs[0]
                  ] + ["\ndiff" + file_diff for file_diff in file_diffs[1:]]
    chunked_file_diffs = []
    for file_diff in file_diffs:
        [head, *chunks] = file_diff.split("\n@@")
        chunks = ["\n@@" + chunk for chunk in chunks]
        chunked_file_diffs.append((head, chunks))
    return chunked_file_diffs


def assemble_diffs(parsed_diffs, cutoff):
    # create multiple well-formatted diff strings, each being shorter than cutoff
    assempled_diffs = [""]
    
    def add_chunk(chunk):
        if len(assempled_diffs[-1]) + len(chunk) >= cutoff:
            assempled_diffs.append(chunk)
            return False
        else:
            assempled_diffs[-1] += "\n" + chunk
            return True
    
    for head, chunks in parsed_diffs:
        if not chunks:
            add_chunk(head)
        while chunks:
            if not add_chunk(chunks[0]):
                assempled_diffs[-1] = head + assempled_diffs[-1]
            chunks = chunks[1:]
    return assempled_diffs


def summarize_diff(diff):
    assert diff
    return complete(DIFF_PROMPT + "\n\n" + diff + "\n\n")


def summarize_summaries(summaries):
    assert summaries
    return complete(COMMIT_MSG_PROMPT + "\n\n" + summaries + "\n\n")


def generate_commit_message(diff):
    if not diff:
        # no files staged or only whitespace diffs
        return "Fix whitespace"
    
    assembled_diffs = assemble_diffs(parse_diff(diff), PROMPT_CUTOFF)
    summaries = "\n".join([summarize_diff(diff) for diff in assembled_diffs])
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
