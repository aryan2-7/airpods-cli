# Contributing

## Setup

```bash
git clone https://github.com/aryan2-7/airpods-cli.git
cd airpods-cli
uv sync
source .venv/bin/activate
uv pip install -e .
```

## Running tests

```bash
uv run pytest -v
```

## Code style

This project uses `ruff` for linting and formatting.

```bash
# Check for issues
uv run ruff check .

# Auto-fix what can be fixed
uv run ruff check . --fix

# Format code
uv run ruff format .
```

## Branch workflow

- `main` — stable releases only
- `dev` — active development
- Feature branches: `feat/command-name` or `fix/issue-description`

Open a PR from your feature branch into `dev`. Do not PR directly into `main`.

## Commit style

Follow Conventional Commits:

- `feat:` new feature
- `fix:` bug fix
- `chore:` tooling, config, setup
- `docs:` documentation only
- `test:` adding or updating tests
- `refactor:` code change with no behaviour change

Example: `feat: add airpods status command`
