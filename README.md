# gpt-commit

Generate commit messages using GPT-3. To use `gpt-commit`, simply invoke it whenever you'd use `git commit`. Git will prompt you to edit the generated commit message.

```
git add .
./gpt-commit.py
```

## Getting Started

Install `openai` and clone `gpt-commit`.

```
pip3 install openai
git clone git@github.com:markuswt/gpt-commit.git
```

Set the environment variable `OPENAI_API_KEY` to your [OpenAI API key](https://platform.openai.com/account/api-keys), e.g. by adding the following line to your `.bashrc`.

```
export OPENAI_API_KEY=<YOUR API KEY>
```

Alternatively, you can set the `openai.api_key` variable in `gpt-commit.py`. You can also set `openai.organization` this way (optional).


Create a `~/.git-templates/hooks/prepare-commit-msg` with the following contents:

```sh
#!/bin/sh

[ -f "$GIT_DIR/MERGE_MSG" ] && exit 0

python gpt-commit-message.py >"$1"
```

Run `git init` into existing repositories and this will allow you to output just the message using the default `git commit` command. Useful for rebasing.
