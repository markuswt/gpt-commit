# gpt-commit

Generate commit messages using GPT-3. To use `gpt-commit`, simply invoke it whenever you'd use `git commit`. Git will prompt you to edit the generated commit message.

```
git add .
./gpt-commit.py
```

## Getting Started

Install `requests` and clone `gpt-commit`.

```
pip3 install requests
git clone git@github.com:markuswt/gpt-commit.git
```

Set the environment variable `OPENAI_API_KEY` to your [OpenAI API key](https://platform.openai.com/account/api-keys), e.g. by adding the following line to your `.bashrc`.

```
export OPENAI_API_KEY=<YOUR API KEY>
```

Alternatively, you can set the `OPENAI_API_KEY` variable in `gpt-commit.py`. You can also set `OPENAI_ORG_ID` this way (optional).
