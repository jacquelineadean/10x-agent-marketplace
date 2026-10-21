"""Frames of a local page, captured by a headless Chromium driven over its DevTools pipe.

The browser runs as a separate program with an argument list, never a shell string. It
talks to this process over two inherited pipes (`--remote-debugging-pipe`), so no port
is opened. It reads only the local file it is given and is closed when capture ends.
Pipes are inherited by file descriptor 3 and 4, which only macOS and Linux support.
"""

from __future__ import annotations

import base64
import json
import os
import select
import subprocess
import sys
from types import TracebackType
from typing import Any

from chronicle.connectors.browser.shoot import BrowserError

TIMEOUT = 30.0  # seconds to wait for one reply before giving up on the browser


class Capture:
    """One headless browser holding one page; use it in a `with` block."""

    def __init__(self, browser: str) -> None:
        if sys.platform == "win32":
            raise BrowserError("frame capture runs on macOS and Linux; on Windows build svg,html")
        self.browser = browser
        self.proc: subprocess.Popen[bytes] | None = None
        self.session = ""
        self.next_id = 0
        self.buffer = b""
        self.write_fd = -1
        self.read_fd = -1

    def __enter__(self) -> Capture:
        import fcntl  # POSIX only; the check in __init__ keeps Windows from reaching here

        to_child_r, to_child_w = os.pipe()
        from_child_r, from_child_w = os.pipe()
        # Park the child's ends above 9 so moving them onto 3 and 4 cannot clobber them.
        child_in = fcntl.fcntl(to_child_r, fcntl.F_DUPFD, 10)
        child_out = fcntl.fcntl(from_child_w, fcntl.F_DUPFD, 10)
        os.close(to_child_r)
        os.close(from_child_w)

        def onto_3_and_4() -> None:
            os.dup2(child_in, 3)
            os.dup2(child_out, 4)

        args = [
            self.browser,
            "--headless=new",
            "--disable-gpu",
            "--hide-scrollbars",
            "--remote-debugging-pipe",
            "--no-first-run",
            "--disable-background-networking",
            "--disable-component-update",
            "--force-color-profile=srgb",
        ]
        # Chromium refuses to start its sandbox as root, which is the norm in containers.
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            args.append("--no-sandbox")
        args.append("about:blank")
        try:
            self.proc = subprocess.Popen(  # noqa: S603  argv list, no shell; the browser is one found on PATH or named by the user
                args,
                pass_fds=(3, 4, child_in, child_out),
                preexec_fn=onto_3_and_4,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except OSError as exc:
            os.close(to_child_w)
            os.close(from_child_r)
            raise BrowserError(f"could not start {self.browser}: {exc.strerror}") from exc
        finally:
            os.close(child_in)
            os.close(child_out)
        self.write_fd, self.read_fd = to_child_w, from_child_r
        return self

    def __exit__(
        self,
        kind: type[BaseException] | None,
        exc: BaseException | None,
        trace: TracebackType | None,
    ) -> None:
        self.close()

    def open(self, url: str, width: int, height: int) -> None:
        """Load the page at a fixed viewport and pixel ratio 1."""
        target = self.send("Target.createTarget", {"url": "about:blank"})["targetId"]
        attached = self.send("Target.attachToTarget", {"targetId": target, "flatten": True})
        self.session = attached["sessionId"]
        self.send(
            "Emulation.setDeviceMetricsOverride",
            {"width": width, "height": height, "deviceScaleFactor": 1, "mobile": False},
        )
        self.send("Page.enable")
        self.send("Page.navigate", {"url": url})
        self.evaluate(
            "new Promise(r => { const go = () => document.fonts.ready.then(r);"
            " document.readyState === 'complete' ? go() : addEventListener('load', go); })"
        )

    def evaluate(self, expression: str) -> Any:
        """Run a script in the page and wait for its promise, if it returns one."""
        reply = self.send(
            "Runtime.evaluate",
            {"expression": expression, "awaitPromise": True, "returnByValue": True},
        )
        if "exceptionDetails" in reply:
            raise BrowserError(f"page script failed: {reply['exceptionDetails'].get('text')}")
        return reply.get("result", {}).get("value")

    def png(self, width: int, height: int) -> bytes:
        """The top-left width x height of the page as PNG bytes."""
        clip = {"x": 0, "y": 0, "width": width, "height": height, "scale": 1}
        data = self.send("Page.captureScreenshot", {"format": "png", "clip": clip})["data"]
        return base64.b64decode(data)

    def send(self, method: str, params: dict[str, Any] | None = None) -> Any:
        self.next_id += 1
        message: dict[str, Any] = {"id": self.next_id, "method": method, "params": params or {}}
        if self.session and not method.startswith(("Target.", "Browser.")):
            message["sessionId"] = self.session
        try:
            os.write(self.write_fd, json.dumps(message).encode() + b"\0")
        except OSError as exc:
            raise BrowserError(f"the browser closed its pipe: {exc.strerror}") from exc
        while True:
            reply = json.loads(self._message())
            if reply.get("id") != self.next_id:
                continue  # an event, or a reply to a message sent before
            if "error" in reply:
                raise BrowserError(f"{method} failed: {reply['error'].get('message')}")
            return reply.get("result", {})

    def _message(self) -> bytes:
        while b"\0" not in self.buffer:
            ready, _, _ = select.select([self.read_fd], [], [], TIMEOUT)
            if not ready:
                raise BrowserError(f"the browser did not answer within {TIMEOUT:.0f} s")
            chunk = os.read(self.read_fd, 1 << 20)
            if not chunk:
                raise BrowserError("the browser exited while capturing frames")
            self.buffer += chunk
        raw, self.buffer = self.buffer.split(b"\0", 1)
        return raw

    def close(self) -> None:
        if self.proc is None:
            return
        try:
            self.session = ""
            self.send("Browser.close")
        except BrowserError:
            self.proc.kill()  # it is already gone or stuck; make sure it does not linger
        for fd in (self.write_fd, self.read_fd):
            if fd >= 0:
                os.close(fd)
        self.write_fd = self.read_fd = -1
        try:
            self.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait(timeout=5)
        self.proc = None
