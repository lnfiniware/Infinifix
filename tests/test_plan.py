from infinifix.distro import detect_distro
from infinifix.doctor import filter_actions
from infinifix.modules import audio_sof, huawei_wmi


class DummyRunner:
    def run(self, *_args, **_kwargs):
        class Result:
            returncode = 0
            stdout = ""
            stderr = ""

        return Result()


class DummyCtx:
    def __init__(self) -> None:
        self.runtime = {}
        self.include_advanced = False
        self.distro = detect_distro('ID=ubuntu\nID_LIKE="debian"\nPRETTY_NAME="Ubuntu"\n')
        self.runner = DummyRunner()
        self.probe = {
            "dmi_vendor": "HUAWEI",
            "dmi_product_name": "MateBook D15",
            "lspci": ["00:1f.3 Audio device: Intel Corporation Tiger Lake-LP Smart Sound"],
        }


def test_audio_plan_sets_boot_refresh() -> None:
    ctx = DummyCtx()
    detected = {
        "intel_audio": True,
        "dummy_output": True,
        "aplay_has_devices": False,
        "sof_firmware_package": "sof-firmware",
        "sof_firmware_installed": False,
        "dspcfg_in_sysfs": False,
        "dspcfg_loaded": True,
        "dsp_conf_present": False,
        "grub_param_present": False,
    }
    actions = audio_sof.plan(ctx, detected)
    ids = {row["id"] for row in actions}
    assert "set_dsp_driver_3" in ids
    assert "add_grub_dsp_param" not in ids
    assert ctx.runtime["needs_boot_refresh"] is True


def test_audio_grub_param_is_advanced_only() -> None:
    ctx = DummyCtx()
    ctx.include_advanced = True
    detected = {
        "intel_audio": True,
        "dummy_output": True,
        "aplay_has_devices": False,
        "sof_firmware_package": "sof-firmware",
        "sof_firmware_installed": True,
        "dspcfg_in_sysfs": True,
        "dspcfg_loaded": False,
        "dsp_conf_present": True,
        "grub_param_present": False,
    }
    actions = audio_sof.plan(ctx, detected)
    add_grub = [row for row in actions if row["id"] == "add_grub_dsp_param"][0]
    assert add_grub["advanced"] is True


def test_huawei_wmi_advanced_action() -> None:
    ctx = DummyCtx()
    ctx.runtime["secure_boot"] = True
    detected = {
        "is_huawei": True,
        "wmi_present": False,
        "threshold_paths": [],
    }
    actions = huawei_wmi.plan(ctx, detected)
    ids = {row["id"] for row in actions}
    assert "install_huawei_wmi_dkms" in ids
    advanced = [row for row in actions if row["id"] == "install_huawei_wmi_dkms"][0]
    assert advanced["advanced"] is True


def test_filter_actions_modes() -> None:
    actions = [
        {"id": "safe_1", "safe": True, "advanced": False},
        {"id": "adv_1", "safe": False, "advanced": True},
    ]
    safe_only = filter_actions(actions, include_advanced=False)
    assert [row["id"] for row in safe_only] == ["safe_1"]
    full = filter_actions(actions, include_advanced=True)
    assert {row["id"] for row in full} == {"safe_1", "adv_1"}
