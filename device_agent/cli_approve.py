"""Run this on the Pi itself (e.g. over SSH) to approve or deny actions the
device agent has proposed. This is the approval point for now - it runs on
the Pi, not on whatever computer is plugged in over USB-C.

    python -m device_agent.cli_approve
"""

from .pending_actions import list_pending, resolve


def main() -> None:
    pending = list_pending()
    if not pending:
        print("no pending actions")
        return

    for action in pending:
        print(f"[{action.id}] {action.description}")
        answer = input("  approve? [y/N] ").strip().lower()
        resolve(action.id, approved=(answer == "y"))


if __name__ == "__main__":
    main()
