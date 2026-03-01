from infinifix.main import build_parser


def test_doctor_all_yes_flags() -> None:
    parser = build_parser()
    args = parser.parse_args(["doctor", "--all", "--yes"])
    assert args.command == "doctor"
    assert args.all is True
    assert args.yes is True


def test_apply_yes_flag() -> None:
    parser = build_parser()
    args = parser.parse_args(["apply", "--all", "--yes"])
    assert args.command == "apply"
    assert args.all is True
    assert args.yes is True


def test_subcommands_exist() -> None:
    parser = build_parser()
    subparsers_action = next(action for action in parser._actions if action.dest == "command")
    choices = set(subparsers_action.choices.keys())
    assert {"doctor", "report", "apply", "revert", "status"}.issubset(choices)


def test_parser_version_flag_exits_cleanly(capsys) -> None:
    parser = build_parser()
    try:
        parser.parse_args(["--version"])
    except SystemExit as exc:
        assert exc.code == 0
    out = capsys.readouterr().out
    assert "infinifix" in out.lower()
