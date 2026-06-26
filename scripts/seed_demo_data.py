from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.config import get_settings
from backend.services.demo_data import seed_demo_data


def _demo_tools_allowed() -> bool:
    settings = get_settings()
    if settings.is_production and not settings.enable_demo_tools:
        print("Demo seed: blocked")
        print("Reason: APP_ENV=production requires ENABLE_DEMO_TOOLS=true.")
        print("Secrets exposed: no")
        return False
    return True


def main() -> int:
    if not _demo_tools_allowed():
        return 1

    try:
        status = seed_demo_data()
    except Exception as exc:
        print("Demo seed: failed")
        print(f"Error type: {exc.__class__.__name__}")
        print("Secrets exposed: no")
        return 1

    print("Demo seed: ok")
    print(f"Status: {status['status']}")
    print(f"Products: {status['products']}")
    print(f"Competitors: {status['competitors']}")
    print(f"Quote requests: {status['quote_requests']}")
    print("Sample data: demo only")
    print("Secrets exposed: no")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
