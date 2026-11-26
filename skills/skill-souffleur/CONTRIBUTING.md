# Contributing

Thanks for taking the time to help. Souffleur is maintained by one person, so small, focused changes are the easiest to review.

## Before you start

For anything larger than a typo or a one-line fix, open an issue first and describe the problem. A short discussion up front saves you from writing a pull request that does not fit.

## Pull requests

- Branch from `main` and keep one change per pull request.
- Add or update tests for any change in behaviour.
- Write commit messages in the [Conventional Commits](https://www.conventionalcommits.org/) format, for example `fix: keep the ledger after a resumed session`.
- Update `CHANGELOG.md` under "Unreleased" if users will notice the change.
- If users will notice the change, also raise `version` in `.claude-plugin/plugin.json` and in the plugin entry of `.claude-plugin/marketplace.json` (patch for a fix, minor for a new feature). Claude Code compares this number, so without a new one `claude plugin update` reports "already at the latest version" and the change never reaches an installed copy. A test fails when the two files differ.

Pull requests are merged with squash, so the pull request title becomes the commit message. Write it in the same format.

## Versions and releases

The version in `plugin.json` and `marketplace.json` follows [Semantic Versioning](https://semver.org/). Do not touch the `CHANGELOG.md` headings in a pull request: the maintainer moves the "Unreleased" entries under the new version when tagging. The maintainer also creates the tag `v<version>`, for example `v0.1.0`.

When you check Souffleur on a newer Claude Code version, add the behaviour and the version to [docs/compatibility.md](docs/compatibility.md) and set `VERIFIED_UP_TO` in `src/core/version.ts` to the same version. A test compares the two. `/souffleur` tells users when their Claude Code is newer than that version.

## Checks in CI

The `mod` job installs the Claude Code version named in `VERIFIED_UP_TO` and runs `claude plugin validate .` and `claude plugin test .`. A weekly workflow runs both against the latest Claude Code and opens an issue titled "Mod checks fail on Claude Code <version>" when one fails. Neither command needs a login. Run them locally before you push a change to `src/mod/`.

## Reporting bugs

Use the bug report form. Include your Claude Code version (`claude --version`): hook and plugin behaviour changes between releases, and most bugs depend on it.
