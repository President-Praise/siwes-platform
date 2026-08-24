"""Refresh all fields (TOC, LOF, LOT, PAGEREF) in a .docx by driving
LibreOffice via UNO. Must be invoked by LibreOffice's bundled Python
interpreter (it imports the `uno` module that ships inside the app).

Usage:
    /Applications/LibreOffice.app/Contents/Resources/python _lo_refresh.py <docx>

Launches its own headless soffice instance listening on a uniquely-named pipe,
connects, opens the docx, walks every index/field, saves, and quits."""
import os
import pathlib
import subprocess
import sys
import time
import uno
from com.sun.star.beans import PropertyValue


def _prop(name, value):
    p = PropertyValue()
    p.Name = name
    p.Value = value
    return p


def _find_soffice() -> str:
    env = os.environ.get("SOFFICE_BIN")
    if env and os.path.exists(env):
        return env
    for cand in (
        "/Applications/LibreOffice.app/Contents/MacOS/soffice",
        "/usr/bin/soffice",
        "/usr/local/bin/soffice",
        "/opt/homebrew/bin/soffice",
    ):
        if os.path.exists(cand):
            return cand
    raise RuntimeError("soffice binary not found")


def _connect(pipe_name: str, retries: int = 40):
    local_ctx = uno.getComponentContext()
    resolver = local_ctx.ServiceManager.createInstanceWithContext(
        "com.sun.star.bridge.UnoUrlResolver", local_ctx
    )
    url = f"uno:pipe,name={pipe_name};urp;StarOffice.ComponentContext"
    last = None
    for _ in range(retries):
        try:
            return resolver.resolve(url)
        except Exception as exc:
            last = exc
            time.sleep(0.25)
    raise RuntimeError(f"Could not connect to LibreOffice: {last}")


def refresh(docx_path: str) -> None:
    pipe_name = f"siwes_refresh_{os.getpid()}"
    soffice = _find_soffice()
    proc = subprocess.Popen(
        [
            soffice,
            "--headless",
            "--norestore",
            "--nologo",
            "--nofirststartwizard",
            f"--accept=pipe,name={pipe_name};urp;",
            "-env:UserInstallation=file:///tmp/lo_siwes_profile",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        ctx = _connect(pipe_name)
        smgr = ctx.ServiceManager
        desktop = smgr.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)
        url = pathlib.Path(docx_path).resolve().as_uri()
        # ReadOnly=False so we can save back; Hidden so no UI flashes.
        doc = desktop.loadComponentFromURL(
            url, "_blank", 0,
            (_prop("Hidden", True), _prop("ReadOnly", False)),
        )
        if doc is None:
            raise RuntimeError(f"loadComponentFromURL returned None for {url}")
        try:
            # Use dispatcher commands — works for raw w:fldChar TOC fields
            # that don't surface via doc.getDocumentIndexes().
            dispatcher = smgr.createInstanceWithContext(
                "com.sun.star.frame.DispatchHelper", ctx
            )
            frame = doc.getCurrentController().getFrame()
            for cmd in (".uno:UpdateAllIndexes", ".uno:UpdateAllLinks",
                        ".uno:UpdateFields", ".uno:UpdateAll"):
                try:
                    dispatcher.executeDispatch(frame, cmd, "", 0, ())
                except Exception:
                    pass
            doc.refresh()
            # Also try the typed APIs in case some indexes ARE structured.
            try:
                indexes = doc.getDocumentIndexes()
                for i in range(indexes.getCount()):
                    indexes.getByIndex(i).update()
            except Exception:
                pass
            try:
                enum = doc.getTextFields().createEnumeration()
                while enum.hasMoreElements():
                    f = enum.nextElement()
                    if hasattr(f, "update"):
                        try:
                            f.update()
                        except Exception:
                            pass
            except Exception:
                pass
            doc.store()
        finally:
            doc.close(True)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: _lo_refresh.py <docx_path>", file=sys.stderr)
        sys.exit(2)
    refresh(sys.argv[1])
