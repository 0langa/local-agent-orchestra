# Release Checklist

Use this checklist before publishing a new Agentheim release.

## Pre-release Verification

- [ ] All CI checks pass on `master`
- [ ] `python -m pytest -q` passes locally
- [ ] `python -m pytest -q -o addopts=` passes locally
- [ ] `python -m compileall -q agentheim core config interfaces providers presets tools workflows memory agents federation marketplace monitoring multimodal scripts tests` passes
- [ ] `python scripts/roadmap-check.py --ci` passes
- [ ] Docs commands run without error:
  - [ ] `python -m interfaces.cli.cli --help`
  - [ ] `python -m interfaces.cli.cli commands --json`
  - [ ] `python scripts/docs_check.py`
- [ ] Live AI acceptance passes against a configured release profile:
  - [ ] `python scripts/live_validate.py --profile <profile> --max-attempts 1 --delay-between-tests 1`
- [ ] Live tool and vision smoke passes against the same configured profile:
  - [ ] `python scripts/live_tool_smoke.py`
- [ ] Package builds:
  - [ ] `python -m build` produces wheel and sdist
  - [ ] `twine check dist/*` passes
- [ ] Clean wheel install smoke passes:
  - [ ] `python scripts/package_smoke.py`

## Version Bump

- [ ] `CHANGELOG.md` is updated with release notes
- [ ] `pyproject.toml` version is set to the release version
- [ ] Git tag is created: `git tag -a vX.Y.Z -m "Release vX.Y.Z"`

## Distribution

- [ ] Wheel and sdist uploaded to PyPI: `twine upload dist/*`
- [ ] GitHub release created with release notes
- [ ] Source archive attached to GitHub release

## Post-release

- [ ] `pyproject.toml` version is bumped to the next development version
- [ ] `master` branch is fast-forwarded or merged
