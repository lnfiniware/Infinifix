from infinifix.privacy import sanitize_obj, sanitize_text


def test_sanitize_text_masks_email_and_home() -> None:
    text = "user=alice email=alice@example.com home=/home/alice token=abcdefabcdefabcdefabcdef"
    redacted = sanitize_text(text)
    assert "alice@example.com" not in redacted
    assert "/home/alice" not in redacted
    assert "<redacted-email>" in redacted
    assert "/home/<user>" in redacted
    assert "<redacted-hex>" in redacted


def test_sanitize_obj_nested() -> None:
    payload = {"k": ["a@example.com", {"p": "/Users/alice/work"}]}
    redacted = sanitize_obj(payload)
    assert redacted["k"][0] == "<redacted-email>"
    assert redacted["k"][1]["p"] == "/Users/<user>/work"

