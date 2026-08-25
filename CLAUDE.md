# Kiosk Display

A Doover device app that shows a web page on the device's own display. It brings
its own compositor and browser because the target devices have neither.

## Commands

```bash
uv sync
uv run pytest                                    # detection + config generation
uv run export-config && uv run export-ui         # -> doover_config.json
docker buildx build --platform linux/arm64 -t kiosk-display .
```

## Structure

```
src/kiosk_display/display.py      # detect connector, card, modes, GPU usability
src/kiosk_display/session.py      # sway config generation + process supervision
src/kiosk_display/browser.py      # fullscreen WebKitGTK window (standalone)
src/kiosk_display/application.py  # Doover app: config, tags, UI, watchdog
```

## Things that will bite you

- **Two Pythons, on purpose.** PyGObject is compiled against the distro
  interpreter; the app venv is a different minor version and cannot load `_gi`.
  The browser is copied to `/usr/local/lib/kiosk_browser.py` and run with
  `/usr/bin/python3`. Don't "tidy" it into the venv.
- **Never assume `card0`.** The DRM card that owns the connected connector is
  whichever `cardN-<connector>` sysfs entry says; on an i.MX8 the display pipe
  is `card1` and `card0` is the GPU.
- **A render node does not mean Mesa can use it.** i.MX8 exposes `renderD128`
  through NXP's `galcore`, which Mesa cannot drive. `probe_acceleration`
  blacklists vendor-only drivers and falls back to pixman. Guessing optimistically
  gets a compositor that won't start.
- **sway, not cage.** cage is smaller but cannot pin an output mode, and driving
  a 1080p panel at 720p is the single biggest saving when rendering in software.
- **cog's DRM backend segfaults on imx-drm** importing dmabuf, and Alpine 3.23
  dropped the cog package anyway. WebKitGTK under sway is the combination that
  works.
- **File capabilities break `docker load`** on filesystems that can't store
  `security.*` xattrs (the Quantum's overlay) — and it fails the whole image, not
  just the file. sway and gstreamer's PTP helper both ship them. The Dockerfile
  strips every capability with `getcap -r / | setcap -r` **inside the same RUN as
  the apk add**. Layers are additive: stripping in a later RUN leaves the xattr
  in the layer underneath and `docker load` still trips over it. Verify with
  `docker save img | grep -c security.capability` — it must be 0.
- **Vendor splashes fight for the framebuffer.** Symptom is the page showing then
  being replaced a second later. See `conflicting_services` in the README.

## Getting the image onto a device by hand

Publish to a registry and `docker pull` where you can. When you must side-load,
stream it — do not stage a tarball on the device first:

```sh
docker save kiosk-display:test | gzip -1 | \
  ssh root@device 'docker load'
```

`/tmp` is tmpfs on these boards. A 250 MB tarball written there is 250 MB of a
3.6 GB device's RAM, and doing it while the kiosk browser is running was enough
to starve sshd on a Quantum already at load 9 — the box stayed pingable and
stopped answering SSH. Stream into `docker load`, or stage on `/config`, which
is real storage.
