# Changelog

## 1.0.2 — 2026-07-15

- Fix models.py: restore missing InstalledFlake and RegistryConfig classes
- Sync generator endpoint to public repo

## 1.0.1 — 2026-07-15

- Normalize cog code style across all flakes
- Add `flaken update` command
- Add `--style` flag to `flaken add` (hybrid, prefix, appcmd)
- Add command_style field to flake manifests
- Update docs with command style reference
- Add GitHub Actions: CI tests + PyPI publish

## 1.0.0 — 2026-07-15

- Initial release
- CLI: init, search, add, list, remove, info
- Flakes: leveling, moderation, welcome
- Registry API: list, get, download, publish
- Bot generator page
