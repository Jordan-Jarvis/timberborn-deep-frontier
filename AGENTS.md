# Timberborn development

Use the maintained Timberborn skill at `C:/Users/Jordan/.codex/skills/timberborn-modding/SKILL.md` for work in this project. Update its relevant references when a verified discovery changes the workflow; separate source evidence, runtime results, and hypotheses.

Use official Timberborn methods first. `tools/build_deep_frontier.ps1` invokes the official Mod Builder; do not recreate its packaging or installation logic.

Do not add normalization or fallback logic. Correct the producing source and make invalid inputs fail explicitly.

Machine paths (game, Workshop, Documents, Node, Python, PowerShell 7, Blender, Unity) come from `tools/dev-environment.json`, written by `python tools/setup_dev.py`; scripts read it through `tools/dev_environment.py`, `tools/dev_environment.mjs` and `tools/DevEnvironment.ps1` and never hard-code a path. Never commit game assets: `tools/check_no_game_assets.py` (pre-commit hook and validate_all check) enforces it. Tools not on PATH on this machine: PowerShell 7 (`pwsh`, required by `tools/validate_all.ps1` and `tools/scratch_mirror.ps1`) is `C:/Users/Jordan/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe`; node and python are in the same `dependencies` folder (`node/bin/node.exe`, `python/python.exe`).

Isolated testing never copies the repository. Generate and validate in a persistent scratch mirror: `pwsh tools/scratch_mirror.ps1 -Name <task>` prints its root (`%USERPROFILE%\dfs\<task>`), re-syncs only changed files in about a second, and links the large read-only inputs (vendor, Blender scenes, docs/art, node_modules, Blender). Re-run it before each test; it discards scratch-only edits. Never write through its links, never generate into the real `src/DeepFrontier/Data`, and run Blender saves and exports only in the real repository. Compile with an incremental `dotnet build` (never `--no-incremental`), and run only the checks a change touches with `tools/validate_all.ps1 -Only <ids>` before one full run at the end.

Target Timberborn 1.1 and Iron Teeth. Read `docs/implementation-plan.md` for scope and `tools/STATUS.md` for actual implementation and verification state. Keep intended features distinct from completed, tested behavior.
