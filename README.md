# Kiosk Display

Show a web page on a Linux device's own display, and keep it there.

The app brings its own graphics session — compositor, browser and software
renderer — because the devices this targets generally have none. A typical
industrial gateway has a KMS-capable kernel and nothing above it: no X, no
Wayland, no browser, often no usable GPU userspace, and a read-only or
package-less root filesystem. Rather than ask the device for a desktop, this
ships one in the container.

## What it does

```
kiosk-display (this app, supervising)
  └── sway                     wlroots compositor, output mode pinned
        └── WebKitGTK window   one URL, fullscreen, no chrome
```

Everything about the display is detected at startup:

| Decision | How it's made |
|---|---|
| Which output | First connected connector under `/sys/class/drm`, or the one named in config |
| Which DRM device | The card that owns that connector — not assumed to be `card0` |
| Which mode | The connector's preferred mode, or the one configured |
| GPU or software | Mesa present **and** a render node **and** no vendor-only driver → GL; otherwise pixman |

That last row is the one that matters in the field. A board can have a GPU the
kernel exposes and Mesa cannot drive — an i.MX8 with NXP's `galcore` is the
common case — and asking for GL there gets a compositor that refuses to start.
Detection is deliberately pessimistic: when unsure it picks software rendering,
which always works.

## Configuration

| Key | Default | Meaning |
|---|---|---|
| `url` | — | The page to display. May be device-local |
| `zoom` | `1.0` | Page zoom. Below 1 fits a desktop layout onto a small panel |
| `output` | auto | Connector, e.g. `HDMI-A-1` |
| `mode` | preferred | e.g. `1280x720@60`. Driving a 1080p panel at 720p roughly halves the work with no GPU |
| `rotation` | `0` | 0 / 90 / 180 / 270, for a panel mounted sideways |
| `renderer` | `auto` | Force `gl` or `pixman` if detection guesses wrong |
| `reload_interval_min` | `0` | Periodic reload; guards against a page that wedges after weeks |
| `hide_cursor` | `true` | There is rarely a mouse |
| `ignore_tls_errors` | `true` | Device-local pages use self-signed certificates |
| `conflicting_services` | — | Init scripts to stop first (see below) |

## Vendor splash screens

Some vendor images run their own status screen on the framebuffer and will
repaint over anything else — the symptom is your page appearing for a moment and
being replaced a second later. Name the init scripts in `conflicting_services`
and they are stopped before the session starts.

On an ELPRO Quantum that's `S01splash` **and** `S89splash` — the same Qt splash
registered twice, and stopping only one leaves the other to fight you.

Stopping them at boot is a separate, permanent change to the device and is left
to the operator; this app only stops them while it runs. Doing it permanently
means renaming them out of `rcS`'s `S??*` glob, since Buildroot's `rcS` runs
each match without checking the execute bit:

```sh
mv /etc/init.d/S89splash /etc/init.d/disabled.S89splash
```

## Requirements

The container needs real access to the display hardware:

```yaml
privileged: true          # DRM master
volumes:
  - /dev/dri:/dev/dri
  - /run/udev:/run/udev:ro
  - /etc/init.d:/host/etc/init.d:ro   # only for conflicting_services
```

## Development

```bash
uv sync
uv run pytest                       # detection and config-generation logic
uv run export-config && uv run export-ui
docker buildx build --platform linux/arm64 -t kiosk-display .
```

The browser deliberately runs on the **distro** Python rather than the app venv:
PyGObject is a compiled extension built against the distro interpreter, and the
venv is on a different minor version. The supervising app keeps its venv; the
window it launches gets a standalone script and the interpreter that can load
`_gi`.

## Project map

| Path | Purpose |
|---|---|
| `src/kiosk_display/display.py` | Detection — connector, card, modes, whether Mesa can help |
| `src/kiosk_display/session.py` | Compositor config generation and process supervision |
| `src/kiosk_display/browser.py` | The fullscreen WebKit window (standalone, distro Python) |
| `src/kiosk_display/application.py` | Doover app: config, tags, UI, watchdog |
| `tests/` | Detection and config-generation, which have to cope with unfamiliar hardware |

## Relationship to `doover-kiosk`

`doover-kiosk` is the apt package for Raspberry Pi devices, running WebKitGTK
under labwc on the Pi desktop. It is more capable on that hardware — autologin,
reload button, memory watchdog, sticky settings — and a Pi has a working GPU and
a package manager, so it needs none of what this app carries.

This app exists for devices where that isn't true, and for fleets that would
rather configure a display from the Doover UI than over SSH. The two share an
engine choice (WebKitGTK) but not a delivery mechanism.
