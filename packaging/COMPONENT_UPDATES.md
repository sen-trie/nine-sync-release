# Automated Core and FX dependency PR

One rolling pull request keeps the pinned `nine-sync-core` and `nine-sync-fx` submodules on the newest stable
releases. It is never merged automatically, and merging it never publishes anything.

| File | Role |
| --- | --- |
| `.github/workflows/update-components.yml` | Listens for `repository_dispatch` `component_released` (and manual dispatch); runs the updater |
| `packaging/update_components.py` | Verifies, selects, compatibility-checks, then maintains the branch and PR through the GitHub API (no submodule code is fetched or run) |
| `packaging/components.json` | Approved Core/FX repositories, branch `automation/update-components`, PR title |
| `.github/workflows/pr-validation.yml` | Build, static validation, Blender validation and unit tests on every PR update, against the PR head commit |
| `packaging/test_update_components.py` | Offline tests (fake GitHub API) and workflow safety policy tests |

## Behaviour

1. The notification payload `{component, repository, tag, commit}` is only a trigger. It must name an approved
   repository and component, a stable `X.Y.Z` tag, a published non-draft non-prerelease release whose tag resolves
   (annotated or lightweight) to the reported commit. The commit must be on the component's default branch and its
   `blender_manifest.toml` version must equal the tag.
2. The updater then resolves the latest eligible stable release of **both** components itself, so duplicate, late
   or out-of-order notifications cannot downgrade anything or drop the other component's update.
3. A component only moves when its latest release is newer than what `main` pins.
4. Core/FX must be compatible, using the rules `validate_bundle.py` already enforces: shared major.minor with each
   other and with `packaging/bundle/blender_manifest.toml`, byte-identical `hooks.py`, `API_VERSION = 1`.
   If not, the run fails, nothing is written and the last compatible state stays.
   (A new Core/FX minor therefore needs the Bundled version raised on `main` first; that is a release decision.)
5. The branch is derived entirely from `main` plus the new pins and written as a single commit through the Git
   data API, so a late `main` change is picked up and nothing accumulates. Every push to the PR counts as new
   commits, which dismisses stale approvals when that repository setting is on.
6. If anyone pushed their own commit or touched another path on the branch, the run fails with a conflict report
   and does not overwrite it.
7. Runs are serialized (`concurrency: update-components`, no cancel of a running job).

## Required GitHub setup (not done by these files)

**GitHub App** (preferred over a PAT): install on the Bundled repository only, with `Contents: read & write`
and `Pull requests: read & write` (Metadata read is implicit). No Workflows, Actions or Administration permission.
Store in the Bundled repository: variable `COMPONENT_UPDATE_APP_CLIENT_ID`, secret `COMPONENT_UPDATE_APP_PRIVATE_KEY`.
An app token is needed because pushes and PRs made with `GITHUB_TOKEN` do not start `pr-validation.yml`.
Core and FX are public, so reads need no extra grant. If they become private, install the app on them with
`Contents: read` and add them to `repositories` in the workflow.

**Sending the notification** (from the Core and FX release workflows, after a stable release is published): a
credential allowed to call `POST /repos/<bundled>/dispatches`, which GitHub gates on `Contents: write` on Bundled.
Use a second, minimal GitHub App or a fine-grained PAT limited to the Bundled repository with only that permission,
stored as a secret in Core and FX. The payload is re-verified, so the worst a leaked credential can do is trigger a
re-check. Ready-to-paste step: `outbox/` handoff `component_released_notification.md`.

**Branch ruleset on `main`** (the only way to enforce approval and checks):

- Require a pull request with at least 1 approval, and *Dismiss stale approvals when new commits are pushed*.
- Require status check `PR validation result` (and require the branch to be up to date).
- Do not allow bypass; do not enable auto-merge.
- Restrict who can push to `main`; the app only writes `automation/update-components`.

**Environments** `release`, `extension-repository`, `experimental-release` keep their required reviewers. Merge to
`main` triggers none of them: `release.yml` and `experimental-release.yml` are `workflow_dispatch` only.

## Local checks

```
python -I packaging/test_update_components.py
GITHUB_REPOSITORY=<owner>/<bundled> python -I packaging/update_components.py update --dry-run   # read-only
```

## Changelog and draft release notes

`CHANGELOG.md` (repo root) is Bundled's own changelog: packaging, installation and integration only. Core and FX keep theirs.

- Add Bundled entries under `[Unreleased]`. The version and the changelog are not touched until a release is authorised;
  then run `python -I packaging/release_notes.py finalize --version X.Y.Z --date YYYY-MM-DD` (moves `[Unreleased]`
  under the version, keeps all history) and bump the manifest by hand.
- Every update of the rolling PR appends **draft release notes** to the PR body. At release time `release.yml` builds the
  same notes into the draft GitHub release (also attached as `release-notes.md`). It is still a draft: a person edits and publishes it.
- Baseline: the `artifact-manifest.json` of the newest published (non-draft) Bundled release. Notes cover every
  published Core/FX version after the baseline up to the built one, including intermediate releases, with links to
  their GitHub Releases. Bullets come from each component's `CHANGELOG.md` at the release commit (so unreleased entries cannot
  appear), condensed to the first sentence. A version without a changelog section is reported as missing, never filled in.
  No baseline or no readable manifest is stated in the notes instead of guessed.
- Bundled-specific section: `[Unreleased]` verbatim plus factual bundled-dependency version changes between manifests.
