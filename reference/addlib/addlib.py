"""Addlib Media Manager - move normalized media files into media library folders."""

import argparse
import os
import sys

from addlib_core import move_and_rename, default_logger


def run_interactive():
    """Interactive CLI: prompt for source, target, type, organize_by_initial."""
    source_directory = input("Enter the source root directory path: ").strip()
    if not source_directory or not os.path.isdir(source_directory):
        print(f"'{source_directory}' is not a valid directory. Exiting...")
        sys.exit(1)

    target_directory = input("Enter the target root directory path: ").strip()
    if not target_directory or not os.path.isdir(target_directory):
        print(f"'{target_directory}' is not a valid directory. Exiting...")
        sys.exit(1)

    content_type = input("Enter content type (movie or tv_series): ").strip().lower()
    if content_type not in ["movie", "tv_series"]:
        print("Invalid content type. Please enter 'movie' or 'tv_series'. Exiting...")
        sys.exit(1)

    organize_by_initial = (
        input("Organize by initial character? (yes or no): ").strip().lower() == "yes"
    )

    move_and_rename(
        source_directory,
        target_directory,
        content_type,
        organize_by_initial,
        logger=default_logger,
    )
    print("\nOperations completed.")


def run_rule_by_name(rule_name: str):
    """Run a single rule from config by name."""
    from addlib_config import load_rules, validate_rule

    rules = load_rules()
    rule = next((r for r in rules if r.get("name") == rule_name), None)
    if not rule:
        print(f"Rule not found: {rule_name}")
        sys.exit(1)
    ok, err = validate_rule(rule)
    if not ok:
        print(f"Validation error: {err}")
        sys.exit(1)
    move_and_rename(
        rule["source"],
        rule["target"],
        rule["type"],
        rule.get("organize_by_initial", False),
        logger=default_logger,
    )
    print(f"\nCompleted rule: {rule_name}")


def run_ui():
    """Launch the Flet GUI."""
    import flet as ft
    from addlib_ui import main
    ft.run(main)


def main():
    parser = argparse.ArgumentParser(
        description="Addlib Media Manager - move normalized media into library folders"
    )
    parser.add_argument(
        "--cli",
        action="store_true",
        help="Run interactive CLI instead of GUI",
    )
    parser.add_argument(
        "--rule",
        metavar="NAME",
        help="Run a single rule from config by name",
    )
    args = parser.parse_args()

    if args.rule:
        run_rule_by_name(args.rule)
    elif args.cli:
        run_interactive()
    else:
        run_ui()


if __name__ == "__main__":
    main()
