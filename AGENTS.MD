# AGENTS Guide

This file gives coding agents the minimum context needed to work safely and consistently in this repository.

## Project

- Name: GoalSite2
- Type: Python + Pygame 2D football simulation
- Entry point: `main.py`
- Main gameplay module: `goalsite2/game.py`
- Config file: `config/game_config.json`

## Environment

- OS target: Windows
- Python environment: use the existing local virtual environment at `.venv`
- Install dependencies with:
  - `.venv/Scripts/python.exe -m pip install -r requirements.txt`

## Run

- Default run:
  - `.venv/Scripts/python.exe main.py`
- Run with explicit config:
  - `.venv/Scripts/python.exe main.py config/game_config.json`

## Current Gameplay Scope

- Dot-based players and ball.
- One human-controlled random player (when enabled in config).
- Other players are stationary by default.
- Halftime side switch is implemented.
- Stamina exists and sprint consumes/regenerates stamina.
- Stamina bars and player role labels are displayed.

## Controls

- Move: Arrow keys
- Sprint: `E`
- Attack:
  - `S`: short pass
  - `A`: long pass
  - `D`: shot
- Defense:
  - `W`: normal tackle

## Coding Rules

- Keep changes minimal and focused.
- Preserve existing file layout and naming unless explicitly requested.
- Do not add new dependencies unless necessary.
- Update `PLAN.MD` if behavior/spec changes.
- Keep `.venv/` untracked.

## Git Workflow

- Do not commit unless explicitly asked.
- Before committing, verify `.venv` is not tracked.
- Use clear, task-focused commit messages.
- Commit message format: start with a capital letter and do not end with punctuation.
  - Examples: `Initial commit`, `Add .gitignore file`

## Validation

After code changes, run at least:

- Static check for errors in changed files.
- A quick launch test via `main.py` in the existing `.venv`.
