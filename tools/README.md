# Maintainer tools

Use `scripts/validate_version.py` and `scripts/check_artifacts.py` for release checks.
`scripts/import_and_validate.py` is a one-time local provisioning helper, never a CI job.
It refuses to overwrite an existing profile and never deletes the original input file.
