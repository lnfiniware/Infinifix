from __future__ import annotations

import argparse
import sys

from rich.prompt import Confirm

from . import __version__
from .doctor import (
    apply_selected_actions,
    build_context,
    revert_latest,
    run_doctor_preview,
    run_report,
    show_status,
)
from .lock import execution_lock
from .ui import banner, line, results_table


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="infinifix", description="InfiniFix - Huawei Linux Doctor")
    parser.add_argument("--dry-run", action="store_true", help="preview only, no changes")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor_parser = subparsers.add_parser("doctor", help="interactive guided flow")
    doctor_parser.add_argument("--all", action="store_true", help="include advanced fixes in plan/apply")
    doctor_parser.add_argument("--yes", action="store_true", help="non-interactive apply confirmation")

    subparsers.add_parser("report", help="generate diagnostic bundle tar.gz")

    apply_parser = subparsers.add_parser("apply", help="apply recommended safe fixes")
    apply_parser.add_argument("--all", action="store_true", help="include advanced fixes")
    apply_parser.add_argument("--yes", action="store_true", help="non-interactive for advanced mode warning")

    subparsers.add_parser("revert", help="restore latest backup session")
    subparsers.add_parser("status", help="show installed/changed status")
    return parser


def cmd_doctor(args) -> int:
    from .ui import build_console

    console = build_console()
    banner(console)
    ctx = build_context(console, dry_run=args.dry_run, include_advanced=bool(getattr(args, "all", False)))
    if getattr(args, "all", False):
        line(console, "Advanced mode enabled: may install DKMS or firmware updates.", style="warn")
    plans, selected, _summary = run_doctor_preview(ctx)

    if not selected:
        line(console, "Nothing to apply. System looks sane.", style="ok")
        return 0

    if not ctx.runner.is_root() and not args.dry_run:
        line(console, "Not root: diagnosis only. Run with sudo to apply fixes.", style="warn")
        return 0

    if args.dry_run:
        line(console, "Dry-run preview complete. No files were changed.", style="warn")
        return 0

    if getattr(args, "all", False) and not getattr(args, "yes", False):
        if not Confirm.ask("Apply advanced fixes too? This can touch firmware/DKMS.", default=False):
            line(console, "Skipped apply. You can run `infinifix apply --all` later.", style="warn")
            return 0

    if not getattr(args, "yes", False) and not Confirm.ask("Apply fixes now?", default=False):
        line(console, "Skipped apply. You can run `infinifix apply` later.", style="warn")
        return 0

    applied, verified, backup_session = apply_selected_actions(
        ctx,
        plans,
        include_advanced=bool(getattr(args, "all", False)),
    )
    if backup_session:
        line(console, f"Backup saved to {backup_session}", style="ok")
    results_table(console, "Applied", applied)
    results_table(console, "Verify", verified)
    line(console, "All done. One step left: reboot now or later.", style="accent")
    return 0


def cmd_apply(args) -> int:
    from .ui import build_console

    console = build_console()
    banner(console)
    ctx = build_context(console, dry_run=args.dry_run, include_advanced=bool(args.all))

    if args.all:
        line(console, "Advanced mode enabled: may install DKMS or firmware updates.", style="warn")

    plans, selected, _summary = run_doctor_preview(ctx)
    if not selected:
        line(console, "No matching actions found.", style="ok")
        return 0

    if not ctx.runner.is_root() and not args.dry_run:
        line(console, "Apply mode needs root. Re-run with sudo.", style="warn")
        return 1

    if args.dry_run:
        line(console, "Dry-run preview complete. No files were changed.", style="warn")
        return 0

    if args.all and not args.yes and not Confirm.ask("Apply advanced actions now?", default=False):
        line(console, "Cancelled. Run again with --yes to skip this prompt.", style="warn")
        return 0

    applied, verified, backup_session = apply_selected_actions(ctx, plans, include_advanced=bool(args.all))
    if backup_session:
        line(console, f"Backup saved to {backup_session}", style="ok")
    results_table(console, "Applied", applied)
    results_table(console, "Verify", verified)
    line(console, "All done. One step left: reboot now or later.", style="accent")
    return 0


def cmd_report(args) -> int:
    from .ui import build_console

    console = build_console()
    banner(console)
    ctx = build_context(console, dry_run=args.dry_run, include_advanced=False)
    path = run_report(ctx)
    line(console, f"Report bundle: {path}", style="ok")
    return 0


def cmd_revert(args) -> int:
    from .ui import build_console

    console = build_console()
    banner(console)
    ctx = build_context(console, dry_run=args.dry_run, include_advanced=False)

    if not ctx.runner.is_root() and not args.dry_run:
        line(console, "Revert mode needs root. Re-run with sudo.", style="warn")
        return 1

    rows = revert_latest(ctx)
    results_table(console, "Revert", rows)
    line(console, "All done. One step left: reboot now or later.", style="accent")
    return 0


def cmd_status(args) -> int:
    from .ui import build_console

    console = build_console()
    banner(console)
    ctx = build_context(console, dry_run=args.dry_run, include_advanced=False)
    show_status(ctx)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        with execution_lock():
            if args.command == "doctor":
                return cmd_doctor(args)
            if args.command == "apply":
                return cmd_apply(args)
            if args.command == "report":
                return cmd_report(args)
            if args.command == "revert":
                return cmd_revert(args)
            if args.command == "status":
                return cmd_status(args)
    except RuntimeError as exc:
        print(str(exc))
        return 1

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
