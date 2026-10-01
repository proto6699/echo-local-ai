#!/usr/bin/env python3
from __future__ import annotations

import argparse

from .config import Settings
from .loop import NecoRuntime


def main() -> int:
    parser = argparse.ArgumentParser(description="Neco resident runtime")
    parser.add_argument("--test", action="store_true", help="post one thought and exit")
    args = parser.parse_args()
    try:
        settings = Settings.from_env()
    except (ValueError, OSError) as exc:
        print(f"[config] {exc}")
        return 2
    return NecoRuntime(settings).run(test_mode=args.test)


if __name__ == "__main__":
    raise SystemExit(main())
