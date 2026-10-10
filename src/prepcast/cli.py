"""Command-line interface: `prepcast generate | backtest`."""
from __future__ import annotations

import argparse
import sys

import pandas as pd

from prepcast.config import DATA_DIR, DEFAULT_CONFIG
from prepcast.generator import generate_all


def cmd_generate(args: argparse.Namespace) -> None:
    from prepcast.menu import MENU

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    out = generate_all(DEFAULT_CONFIG)
    out["calendar"].to_csv(DATA_DIR / "calendar.csv", index=False)
    out["covers"].to_csv(DATA_DIR / "covers.csv", index=False)
    out["sales"].to_csv(DATA_DIR / "sales.csv", index=False)
    out["latent_demand"].to_csv(DATA_DIR / "_truth_latent_demand.csv", index=False)
    pd.DataFrame([m.__dict__ for m in MENU]).to_csv(DATA_DIR / "menu.csv", index=False)
    print(f"Wrote calendar/covers/sales/menu/_truth_latent_demand CSVs to {DATA_DIR}")


def _load():
    def rd(name):
        return pd.read_csv(DATA_DIR / name, parse_dates=["date"])

    if not (DATA_DIR / "sales.csv").exists():
        raise SystemExit("No data yet - run `prepcast generate` first.")
    return rd("calendar.csv"), rd("covers.csv"), rd("sales.csv")


def cmd_backtest(args: argparse.Namespace) -> None:
    from prepcast.report import backtest_report

    calendar, covers, sales = _load()
    print(backtest_report(calendar, covers, sales, n_folds=args.folds,
                          compare_censoring=not args.quick, out_dir=DATA_DIR))


def cmd_simulate(args: argparse.Namespace) -> None:
    from prepcast.report import savings_report

    path = DATA_DIR / "backtest_dishes.csv"
    if not path.exists():
        raise SystemExit("No backtest predictions yet - run `prepcast backtest` first.")
    preds = pd.read_csv(path, parse_dates=["date", "origin"])
    latent = pd.read_csv(DATA_DIR / "_truth_latent_demand.csv", parse_dates=["date"])
    print(savings_report(preds, latent, out_dir=DATA_DIR))


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="prepcast")
    sub = parser.add_subparsers(dest="command", required=True)

    p_gen = sub.add_parser("generate", help="Generate the synthetic dataset")
    p_gen.set_defaults(func=cmd_generate)

    p_bt = sub.add_parser("backtest", help="Rolling-origin backtest vs baselines")
    p_bt.add_argument("--folds", type=int, default=52)
    p_bt.add_argument("--quick", action="store_true", help="skip the censoring comparison run")
    p_bt.set_defaults(func=cmd_backtest)

    p_sim = sub.add_parser("simulate", help="Prep/waste simulation on the backtest weeks")
    p_sim.set_defaults(func=cmd_simulate)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    sys.exit(main())
