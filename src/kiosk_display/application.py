import logging
import os
import shlex

from pydoover import ui
from pydoover.docker import Application

from .app_config import KioskDisplayConfig
from .app_tags import KioskDisplayTags
from .app_ui import KioskDisplayUI
from . import display as display_mod
from .session import Session, build_sway_config, session_environment, stop_conflicting_services

log = logging.getLogger(__name__)


class KioskDisplayApplication(Application):
    """Put a web page on the device's own display and keep it there.

    The app owns a compositor and a browser as child processes. Its main loop is
    a watchdog: if the session dies — a wedged browser, a panel unplugged and
    replugged, a vendor splash winning a fight for the framebuffer — it brings
    the whole thing back rather than leaving a black screen nobody notices.
    """

    config_cls = KioskDisplayConfig
    tags_cls = KioskDisplayTags
    ui_cls = KioskDisplayUI

    config: KioskDisplayConfig
    tags: KioskDisplayTags

    async def setup(self):
        self.session = Session()
        self._restarts = 0
        await self.start_session()

    async def start_session(self):
        """Detect the display, then bring up the session on it."""
        await self.tags.showing.set(False)

        stopped = await stop_conflicting_services(list(self.config.stop_services.value or []))
        if stopped:
            log.info("Stopped before starting: %s", ", ".join(stopped))

        found = display_mod.detect(self.config.output.value or "")
        await self.tags.display_found.set(found is not None)
        if found is None:
            await self.tags.last_error.set("No connected display found")
            log.error("No connected display; will retry")
            return

        mode = display_mod.resolve_mode(found, self.config.mode.value or "")
        renderer = self.config.renderer.value or "auto"
        effective = "gl" if (found.accelerated if renderer == "auto" else renderer == "gl") else "pixman"

        log.info(
            "Display %s on %s, mode %s, renderer %s (%s)",
            found.connector, found.device, mode, effective,
            "auto-detected" if renderer == "auto" else "forced",
        )

        config_text = build_sway_config(
            display=found,
            mode=mode,
            rotation=int(self.config.rotation.value or 0),
            hide_cursor=bool(self.config.hide_cursor.value),
            browser_command=self._browser_command(),
        )

        try:
            await self.session.start(config_text, session_environment(found, renderer))
        except Exception as exc:  # noqa: BLE001 — surface any startup failure as a tag
            await self.tags.last_error.set(str(exc)[:200])
            log.exception("Could not start the display session")
            return

        await self.tags.output.set(found.connector)
        await self.tags.mode.set(str(mode) if mode else "preferred")
        await self.tags.renderer.set(effective)
        await self.tags.url.set(self.config.url.value or "")
        await self.tags.last_error.set("")
        await self.tags.showing.set(True)

    #: The browser runs on the distro Python rather than the app's venv — see
    #: the Dockerfile. Overridable so it can be pointed at a dev checkout.
    BROWSER = os.environ.get(
        "KIOSK_BROWSER_COMMAND", "/usr/bin/python3 /usr/local/lib/kiosk_browser.py"
    )

    def _browser_command(self) -> str:
        args = [*self.BROWSER.split(), self.config.url.value or "about:blank"]
        if self.config.zoom.value:
            args += ["--zoom", str(self.config.zoom.value)]
        if self.config.ignore_tls_errors.value:
            args.append("--ignore-tls")
        if self.config.reload_minutes.value:
            args += ["--reload-minutes", str(self.config.reload_minutes.value)]
        return shlex.join(args)

    async def main_loop(self):
        if self.session.running:
            await self.tags.showing.set(True)
            return

        # The session is down. Whether it never started or fell over, the fix is
        # the same, and doing it quietly beats a dark screen.
        self._restarts += 1
        await self.tags.restarts.set(self._restarts)
        await self.tags.showing.set(False)
        log.warning("Display session is not running; restarting (attempt %s)", self._restarts)

        await self.session.stop()
        await self.start_session()

    @ui.handler("restart")
    async def on_restart(self, ctx, value):
        log.info("Restart requested from the Doover UI")
        await self.session.stop()
        await self.start_session()

    async def on_shutdown(self):
        await self.session.stop()
