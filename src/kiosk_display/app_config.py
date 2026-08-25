from pathlib import Path

from pydoover import config


class KioskDisplayConfig(config.Schema):
    """Everything is optional except the URL.

    Defaults are all "work it out": the app finds the connected display, its
    preferred mode, and whether the GPU can be used, so a bare install on
    unfamiliar hardware still shows the page.
    """

    url = config.String(
        "URL",
        description="The page to display. May be a device-local address.",
    )

    zoom = config.Number(
        "Zoom",
        default=1.0,
        minimum=0.25,
        maximum=4.0,
        description=(
            "Page zoom. Below 1 fits more on screen — useful for driving a "
            "dashboard designed for a desktop onto a 720p panel."
        ),
    )

    output = config.String(
        "Output",
        default=None,
        description=(
            "Connector to use, e.g. 'HDMI-A-1'. Leave blank to use the first "
            "connected output."
        ),
    )

    mode = config.String(
        "Mode",
        default=None,
        description=(
            "Display mode, e.g. '1280x720@60'. Leave blank for the panel's "
            "preferred mode. Driving a 1080p panel at 720p roughly halves the "
            "work when there is no GPU."
        ),
    )

    rotation = config.Enum(
        "Rotation",
        default="0",
        choices=["0", "90", "180", "270"],
        description="Screen rotation in degrees, for a panel mounted sideways.",
    )

    renderer = config.Enum(
        "Renderer",
        default="auto",
        choices=["auto", "gl", "pixman"],
        description=(
            "'auto' uses the GPU when Mesa can drive it and falls back to "
            "software. Force 'pixman' if the GPU is present but unusable."
        ),
    )

    reload_minutes = config.Number(
        "Reload Interval (min)",
        default=0.0,
        minimum=0.0,
        description=(
            "Reload the page on this interval. 0 never reloads. A guard against "
            "a page that has quietly wedged after weeks on a wall."
        ),
    )

    hide_cursor = config.Boolean(
        "Hide Cursor",
        default=True,
        description="Hide the mouse pointer. There is rarely a mouse.",
    )

    ignore_tls_errors = config.Boolean(
        "Ignore TLS Errors",
        default=True,
        description=(
            "Accept self-signed certificates. Device-local pages are usually "
            "served with one and there is no user to click through the warning."
        ),
    )

    stop_services = config.Array(
        "Conflicting Services",
        element=config.String("Service"),
        description=(
            "Init scripts to stop before starting, for vendor images that run "
            "their own splash on the framebuffer and would repaint over this. "
            "On an ELPRO Quantum: S01splash and S89splash."
        ),
    )


def export():
    KioskDisplayConfig.export(Path(__file__).parents[2] / "doover_config.json", "kiosk_display")


if __name__ == "__main__":
    export()
