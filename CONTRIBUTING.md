# Contributing to Aegis Protocol

Thank you for your interest! Before contributing, please read the [Agent Orientation Guide](AGENTS.md).

## Quick Start
```bash
pip install -e ".[dev]"
pytest tests/ -q
flake8 backend tests scripts --count --select=E9,F63,F7,F82
```

## Branch Naming
- `feat/<scope>` for new features
- `fix/<scope>` for bug fixes
- `docs/<scope>` for documentation updates

## Commit Style
Use [Conventional Commits](https://www.conventionalcommits.org/):
`feat(scout): add Yahoo Finance earnings calendar support`

## Protected Invariants
See Section 2 of [AGENTS.md](AGENTS.md) before touching any frozen benchmark datasets or dossiers.
