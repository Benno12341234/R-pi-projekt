"""Approval queue for actions the AI wants to take on a connected device.

This only records proposals and their approve/deny status - nothing here
executes anything. Wiring an actual action up to `propose()` is deliberately
not done yet: what the AI is allowed to propose, and who approves it, isn't
decided yet (see README.md - "USB-C Device Agent" section)."""

import json
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List, Optional

_STORE = Path("/var/lib/device-agent/pending_actions.json")


@dataclass
class PendingAction:
    id: str
    description: str
    status: str  # "pending" | "approved" | "denied"
    created_at: float


def _load() -> List[dict]:
    if not _STORE.exists():
        return []
    return json.loads(_STORE.read_text())


def _save(actions: List[dict]) -> None:
    _STORE.parent.mkdir(parents=True, exist_ok=True)
    _STORE.write_text(json.dumps(actions, indent=2))


def propose(description: str) -> PendingAction:
    action = PendingAction(
        id=str(uuid.uuid4())[:8],
        description=description,
        status="pending",
        created_at=time.time(),
    )
    actions = _load()
    actions.append(asdict(action))
    _save(actions)
    return action


def list_pending() -> List[PendingAction]:
    return [PendingAction(**a) for a in _load() if a["status"] == "pending"]


def resolve(action_id: str, approved: bool) -> Optional[PendingAction]:
    actions = _load()
    for a in actions:
        if a["id"] == action_id:
            a["status"] = "approved" if approved else "denied"
            _save(actions)
            return PendingAction(**a)
    return None
