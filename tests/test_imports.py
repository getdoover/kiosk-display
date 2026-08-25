"""Smoke tests for the template application.

These validate that modules are importable, the config schema is well-formed,
the Tags/UI classes subclass the correct bases, and the config export entry
point runs end-to-end.
"""

import json

from pydoover.config import Schema
from pydoover.tags import Tags
from pydoover.ui import UI


def test_import_app():
    from kiosk_display.application import KioskDisplayApplication
    assert KioskDisplayApplication.config_cls is not None
    assert KioskDisplayApplication.tags_cls is not None
    assert KioskDisplayApplication.ui_cls is not None


def test_config_schema():
    from kiosk_display.app_config import KioskDisplayConfig
    assert issubclass(KioskDisplayConfig, Schema)

    schema = KioskDisplayConfig.to_schema()
    assert isinstance(schema, dict)
    assert schema["type"] == "object"
    assert len(schema["properties"]) > 0
    assert "a_funny_message" in schema["required"]
    assert "simulator_app_key" in schema["required"]


def test_tags():
    from kiosk_display.app_tags import SampleTags
    assert issubclass(SampleTags, Tags)


def test_ui():
    from kiosk_display.app_ui import KioskDisplayUI
    assert issubclass(KioskDisplayUI, UI)


def test_state_machine():
    from kiosk_display.app_state import KioskDisplayState
    state = KioskDisplayState()
    assert state.state == "off"


def test_config_export(tmp_path):
    from kiosk_display.app_config import KioskDisplayConfig

    fp = tmp_path / "doover_config.json"
    KioskDisplayConfig.export(fp, "kiosk_display")

    data = json.loads(fp.read_text())
    assert "kiosk_display" in data
    assert "config_schema" in data["kiosk_display"]
    assert "properties" in data["kiosk_display"]["config_schema"]


def test_ui_export(tmp_path):
    from kiosk_display.app_ui import KioskDisplayUI

    fp = tmp_path / "doover_config.json"
    KioskDisplayUI(None, None, None).export(fp, "kiosk_display")

    data = json.loads(fp.read_text())
    assert "ui_schema" in data["kiosk_display"]
    assert data["kiosk_display"]["ui_schema"]["type"] == "uiApplication"
    assert "is_working" in data["kiosk_display"]["ui_schema"]["children"]
