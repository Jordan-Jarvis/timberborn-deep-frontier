"""This machine's Timberborn and tool paths, written by tools/setup_dev.py.

    import sys; sys.path.insert(0, '<repo>/tools'); import dev_environment as dev
    dev.resources_assets()   # Path to the game's resources.assets

tools/dev-environment.json is not tracked (each machine has its own). A missing
file or entry is an error that says to run setup; nothing here guesses a path.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / 'tools' / 'dev-environment.json'


def load():
    if not CONFIG.is_file():
        raise SystemExit(f'{CONFIG.relative_to(ROOT)} is missing: run "python tools/setup_dev.py" first '
                         '(add --game <Timberborn folder> if the game is not in a default Steam library).')
    return json.loads(CONFIG.read_text(encoding='utf-8'))


def get(key):
    value = load().get(key)
    if not value:
        raise SystemExit(f'"{key}" is not set in {CONFIG.relative_to(ROOT)}: re-run "python tools/setup_dev.py".')
    return value


def game_root():
    """The game's install folder (holds Timberborn_Data, or Timberborn.app on macOS)."""
    return Path(get('gameRoot'))


def game_data():
    """The folder holding resources.assets and Managed/ (Timberborn_Data, or the app's Resources/Data)."""
    return Path(get('gameData'))


def resources_assets():
    return game_data() / 'resources.assets'


def managed():
    return Path(get('gameManaged'))


def workshop():
    """steamapps/workshop/content/1062090: the subscribed mods."""
    return Path(get('workshopContent'))
