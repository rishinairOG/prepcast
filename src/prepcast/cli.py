"""Command-line interface. Phase 1: `prepcast generate` writes the synthetic CSVs."""
from __future__ import annotations

import argparse
import sys

from prepcast.config import DATA_DIR, DEFAULT_CONFIG
from prepcast.generator import generate_all


def cmd_generate(args: argparse.Namespace) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    out = generate_all(DEFAULT_CONFIG)
    out["calendar"].to_csv(DATA_DIR / "calendar.csv", index=False)
    out["covers"].to_csv(DATA_DIR / "covers.csv", index=False)
    out["sales"].to_csv(DATA_DIR / "sales.csv", index=False)
    out["latent_demand"].to_csv(DATA_DIR / "_truth_latent_demand.csv", index=False)
    import pandas as pd

    from prepcast.menu import MENU

    menu_df = pd.DataFrame([m.__dict__ for m in MENU])
    menu_df.to_csv(DATA_DIR / "menu.csv", index=False)
    print(f"Wrote calendar/covers/sales/menu/_truth_latent_demand CSVs to {DATA_DIR}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="prepcast")
    sub = parser.add_subparsers(dest="command", required=True)

    p_generate = sub.add_parser("generate", help="Generate the synthetic dataset")
    p_generate.set_defaults(func=cmd_generate)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    sys.exit(main())
