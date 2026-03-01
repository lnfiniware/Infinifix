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

