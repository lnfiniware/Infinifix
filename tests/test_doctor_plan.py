from __future__ import annotations

import infinifix.doctor as doctor


class _FakeModule:
    @staticmethod
    def detect(_ctx):
        return {"ok": True}

    @staticmethod
    def plan(_ctx, _detected):
        return []


class _Ctx:
    pass


def test_collect_plan_keeps_modules_with_empty_actions(monkeypatch) -> None:
    monkeypatch.setattr(doctor, "MODULE_ORDER", ["fake_mod"])
    monkeypatch.setattr(doctor, "_load_module", lambda _name: _FakeModule)
    plans = doctor.collect_plan(_Ctx())
    assert "fake_mod" in plans
    assert plans["fake_mod"]["actions"] == []
    assert plans["fake_mod"]["detect"] == {"ok": True}
