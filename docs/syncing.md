# Running a private canon on top of this repo

This repo is the engine. Your company's canon (the notes, the customer directory, the
transcripts) is private and lives somewhere else. The rule that keeps both healthy:

> **Code flows from public to private. Content never flows the other way.**

## Layout

```
your-private-canon/            (private git repo)
├── open-company-brain/        ← this repo, as a git submodule (or a pinned copy)
└── acme/                      ← your project: CB_PROJECT / CB_BASE points here
    └── Context/ …
```

Run the engine against your canon:

```bash
CB_BASE=acme python3 open-company-brain/tools/cb.py stats
```

Install the skill from `open-company-brain/skill/`. Its paths are relative to
`{proyecto}/`.

## Improving the engine while you use it

1. Make the change **here**, in the public repo, against `tools/fixture/` or `example/`.
   Never test against real notes in this repo.
2. Run `python3 tools/test_cb.py`. Then break the thing on purpose and check that the
   suite goes red (C38).
3. Commit. The pre-commit hook runs `tools/leak_check.py --staged` against your private
   denylist.
4. In the private repo, bump the submodule.

If a fix was born from a real case, rewrite the case with fictional names *before* it
enters a test, a comment or a commit message. That is the step where leaks happen.

## The denylist

`tools/leak_check.py` reads one name per line from `$OCB_DENYLIST` or
`~/.config/open-company-brain/denylist.txt`. That file is **never committed**, because
publishing it would be the leak. Build it from your customer directory and entity list,
and add your employer's name and internal domains. CI has no access to it and only runs
the generic patterns, so the hook is the real gate:

```bash
git config core.hooksPath .githooks
```
