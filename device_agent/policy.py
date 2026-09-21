"""Natural-language permission rules, set via voice on the touchscreen
("Regel festlegen" button in display_ui.py). These are handed to the AI as
context before it proposes any action - see display_ui.py's
build_action_prompt(). Rules are plain text; nothing here enforces them in
code beyond "the model was told about them and told to refuse otherwise" -
the actual host-side action is still a stub anyway (see __main__.py).

Storage (path, atomic writes, corruption fallback) is shared with
pending_actions.py - see _store.py."""

from typing import List

from . import _store

_FILE = "policy.json"


def list_rules() -> List[str]:
    return _store.load(_FILE, default=[])


def add_rule(text: str) -> None:
    rules = list_rules()
    rules.append(text)
    _store.save(_FILE, rules)
