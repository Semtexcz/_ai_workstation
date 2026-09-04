# Python Engineering Defaults

Workstation-level defaults for Python work. They apply to new code, new projects, and places without a healthy project-local convention. Inspect the existing repository first: established conventions take precedence. Do not migrate existing projects from Poetry, Black, unittest, argparse, or an established HTTP library solely because these defaults prefer alternatives.

Core rule: prefer ecosystem composition over bespoke implementation.

Decision order:

1. Python standard library when it solves the problem cleanly.
2. Mature, widely adopted library.
3. Established external tool.
4. Custom implementation only when the previous options do not fit.

Do not reimplement solved infrastructure without a concrete reason. These are defaults, not mandatory dependencies.

Preferred defaults when appropriate:

- environment / dependency / package management -> uv
- reusable user-level Python CLI installation -> pipx
- reusable CLI -> Python package + pyproject.toml + `[project.scripts]` entry point; prefer Typer
- reusable CLI under active development -> `pipx install --editable .`; preserve/update the existing editable pipx install rather than duplicating it
- one-off automation -> `uv run`
- project-local Python application -> uv
- tests -> pytest
- linting / formatting -> ruff
- validation / schemas -> pydantic at system boundaries
- typed application settings -> pydantic-settings
- simple synchronous HTTP -> requests with explicit timeouts
- async / advanced HTTP -> httpx with explicit timeouts
- retries / backoff -> tenacity; bounded retries only
- web APIs -> FastAPI
- filesystem paths -> pathlib
- templating -> Jinja2
- numerical work -> numpy, scipy
- tabular data -> polars or pandas according to context

Reusable CLI tools are not loose `python script.py` entry points. They are proper packages exposing `[project.scripts]` so the command is directly callable from the shell. When user-level changes are permitted, install a newly created reusable CLI through pipx; otherwise provide the pipx command. Do not install ordinary project dependencies globally.

Retries must be bounded. Do not blindly retry deterministic validation failures, programming errors, permanent client errors, or unsafe non-idempotent operations.

Use pydantic primarily at system boundaries: external data, API payloads, configuration, validation, serialization. Do not mechanically turn every internal object into a `BaseModel`; plain Python structures suffice when validation adds no benefit.

New projects use pytest and ruff. Typical verification: `uv run ruff check .`, `uv run ruff format --check .`, `uv run pytest`. Bug fixes should normally include regression tests when practical. Do not build custom testing, linting, formatting, HTTP, or retry infrastructure when established tools fit.
