# Contributing

## Commit messages: Conventional Commits

Every commit on main follows [Conventional Commits](https://www.conventionalcommits.org): CI checks each one
(`commitlint.config.mjs`: the conventional rules; body lines may be long).

    <type>(<scope>): <subject in lower case, no final full stop, about 72 characters at most>

    <body: what changed and why, as long as it needs>

- **type**: `feat` (new behaviour), `fix` (a bug), `perf`, `refactor` (no behaviour change), `test`, `docs`,
  `build` (pyproject, uv.lock), `ci` (.github), `chore` (tools, anything else), `style`, `revert`.
- **scope**: the main part touched: `web`, `sim`, `server`, `world`, `account`, `e2e`, `tests`, `music`,
  `design`, `pages`, `tools`, `deps`.
- Breaking changes (`feat!:` or a `BREAKING CHANGE:` footer) make a major release: none so far.

Optional hooks (ruff, and the message check at commit time): `uvx pre-commit install`.

## Releases: tag to release

Nobody bumps a version by hand.

1. A push to main runs `.github/workflows/semantic-release.yml`. python-semantic-release reads the commits
   since the last tag `vX.Y.Z`: a `feat` makes the next minor, a `fix` or `perf` the next patch (while the
   version is 0.x; `major_on_zero = false`). Other types make no release.
2. When there is one, it sets `project.version` in pyproject.toml (and uv.lock), adds it to CHANGELOG.md,
   commits `chore(release): vX.Y.Z`, tags `vX.Y.Z`, pushes, and makes the GitHub Release with the notes.
3. `.github/workflows/release.yml` builds the sdist and wheel (`uv build`) for the tag and attaches them to the
   release. Nothing goes to PyPI.

Preview what the next release would be: `uvx --from python-semantic-release semantic-release --noop version --print`.

## Checks

`.github/workflows/ci.yml` (pull requests and main): ruff, the unit tests (`uv run pytest tests -q
--ignore=tests/e2e`, Python 3.14), prettier on the web client, commit messages. `security.yml` (pull
requests, main, weekly): CodeQL, uv audit, gitleaks, bandit. Not blocking for now: ruff format, prettier,
the ruff rules listed in `ignore` in pyproject.toml, and bandit.
