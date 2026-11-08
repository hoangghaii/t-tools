import argparse
from pathlib import Path

from tvtools import __version__
from tvtools.data.dukascopy import SYMBOLS, fetch_range
from tvtools.data.quality import check_store


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="tvtools")
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser("version", help="Print the installed version")
    data = subcommands.add_parser("data", help="Historical market data")
    data_commands = data.add_subparsers(dest="data_command", required=True)
    fetch = data_commands.add_parser("fetch", help="Download monthly M1 bid and ask")
    fetch.add_argument("--symbol", required=True, choices=sorted(SYMBOLS))
    fetch.add_argument(
        "--from", dest="start", required=True, help="First YYYY-MM month"
    )
    fetch.add_argument("--to", dest="end", required=True, help="Last YYYY-MM month")
    check = data_commands.add_parser("check", help="Write a data quality report")
    check.add_argument("--symbol", required=True, choices=sorted(SYMBOLS))
    args = parser.parse_args(argv)
    if args.command == "version":
        print(__version__)
    elif args.command == "data" and args.data_command == "fetch":
        downloaded, skipped = fetch_range(
            Path("data"), args.symbol, args.start, args.end
        )
        print(f"{args.symbol}: downloaded {downloaded}, skipped {skipped} months")
    elif args.command == "data" and args.data_command == "check":
        print(check_store(Path("data"), args.symbol, Path("reports")))
    return 0
