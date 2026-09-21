"""Natural-language permission rules, set via voice on the touchscreen
("Regel festlegen" button in display_ui.py). These are handed to the AI as
context before it proposes any action - see display_ui.py's
build_action_prompt(). Rules are plain text; nothing here enforces them in
code beyond "the model was told about them and told to refuse otherwise" -
the actual host-side action is still a stub anyway (see __main__.py)."""

import json
from pathlib import Path
from typing import List

_STORE = Path("/var/lib/device-agent/policy.json")


def list_rules() -> List[str]:
    if not _STORE.exists():
        return []
    return json.loads(_STORE.read_text())


def add_rule(text: str) -> None:
    rules = list_rules()
    rules.append(text)
    _STORE.parent.mkdir(parents=True, exist_ok=True)
    _STORE.write_text(json.dumps(rules, indent=2))
