"""The generated compositor config is the contract between this app and sway."""

from kiosk_display.display import Display, Mode
from kiosk_display.session import build_sway_config, session_environment


def make(accelerated=False, dri_path="/usr/lib/dri"):
    return Display(
        connector="HDMI-A-1",
        device="/dev/dri/card1",
        modes=(Mode(1920, 1080),),
        accelerated=accelerated,
        dri_path=dri_path,
    )


class TestSwayConfig:
    def test_pins_the_output_mode(self):
        config = build_sway_config(make(), Mode(1280, 720, 60), 0, True, "kiosk-browser url")
        assert "output HDMI-A-1 mode 1280x720@60Hz" in config

    def test_omits_the_mode_when_using_the_panels_preference(self):
        config = build_sway_config(make(), None, 0, True, "kiosk-browser url")
        assert "output HDMI-A-1 transform normal" in config
        assert "mode" not in config.split("\n")[1]

    def test_applies_rotation(self):
        config = build_sway_config(make(), None, 270, True, "cmd")
        assert "transform 270" in config

    def test_hides_the_cursor_only_when_asked(self):
        assert "hide_cursor" in build_sway_config(make(), None, 0, True, "cmd")
        assert "hide_cursor" not in build_sway_config(make(), None, 0, False, "cmd")

    def test_launches_the_browser(self):
        config = build_sway_config(make(), None, 0, True, "kiosk-browser https://x/ --zoom 0.8")
        assert "exec_always kiosk-browser https://x/ --zoom 0.8" in config


class TestSessionEnvironment:
    def test_software_rendering_when_the_gpu_is_unusable(self):
        env = session_environment(make(accelerated=False))
        assert env["WLR_RENDERER"] == "pixman"
        assert env["LIBGL_ALWAYS_SOFTWARE"] == "1"

    def test_leaves_the_renderer_alone_when_the_gpu_works(self):
        env = session_environment(make(accelerated=True))
        assert "WLR_RENDERER" not in env

    def test_forcing_pixman_overrides_detection(self):
        env = session_environment(make(accelerated=True), force_renderer="pixman")
        assert env["WLR_RENDERER"] == "pixman"

    def test_forcing_gl_overrides_detection(self):
        env = session_environment(make(accelerated=False), force_renderer="gl")
        assert "WLR_RENDERER" not in env

    def test_points_the_compositor_at_the_right_card(self):
        assert session_environment(make())["WLR_DRM_DEVICES"] == "/dev/dri/card1"
