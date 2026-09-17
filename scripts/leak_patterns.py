"""Print store-specific strings that must never appear in tracked files.

The output is stored as the LEAK_PATTERNS GitHub Actions secret, so CI can block them without
the list itself being public. Refresh the secret whenever the local config or app changes:

    python scripts/leak_patterns.py | gh secret set LEAK_PATTERNS
"""

from __future__ import annotations

import os
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def patterns() -> list[str]:
    found: set[str] = set()

    config = ROOT / "config" / "shopify.local.toml"
    if config.exists():
        data = tomllib.loads(config.read_text())
        found.update(data["products"].values())
        found.update(data["variant_metafields"].values())

    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            name, _, value = line.partition("=")
            if name in {"SHOPIFY_STORE", "SHOPIFY_CLIENT_ID"} and value:
                found.add(value)

    for app_config in (ROOT / "apps" / "shopify").glob("shopify.app.*.toml"):
        for line in app_config.read_text().splitlines():
            if line.startswith("client_id"):
                found.add(line.split("=", 1)[1].strip().strip('"'))

    found.update(p for p in os.environ.get("EXTRA_LEAK_PATTERNS", "").split(",") if p)
    return sorted(p for p in found if len(p) >= 6)


if __name__ == "__main__":
    result = patterns()
    if not result:
        sys.exit("No local config, .env or app config found; nothing to protect.")
    print("\n".join(result))
