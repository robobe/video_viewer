# Bullet live video viewer

A standalone Python 3.12 uv project displaying one live SHM image topic per
process. OpenCV shows received FPS, frame sequence, and waiting/live/stale status.
Two viewer processes can independently subscribe to the same camera.

```bash
uv sync --locked
uv run --locked video-viewer --transport-config ../bullet_render/configs/transport.json
# Optional: --topic camera/front/image
uv run --locked pytest -q
```

Start before or after Godot. ZMQ connects to loopback TCP port 5556 by default;
image pixels are copied from the renderer's local POSIX SHM slots through the
shared `bullet_msgs` reader. Requires the same Linux host/user as the renderer
and a graphical desktop. No playback is provided. Settings come from descriptors,
including dimensions, RGB8/BGR8 encoding, and row padding.

Q, Esc, window close, or Ctrl+C releases mappings and sockets. The window keeps
its last image during a publisher outage and resumes on restart. Malformed streams
exit with a diagnostic. Latest-frame display can skip frames; FPS measures copied
frames over elapsed wall time, including idle periods.

The Bullet multi-root workspace includes **Bullet: Video viewer** and opens it
with **Bullet: Open tools** and **Bullet: Run all**. See
[the shared protocol](../bullet_msgs/README.md) for locking and crash cleanup.
