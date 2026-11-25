#!/usr/bin/env python3
"""Tiny NordVPN country switcher. Listens only on this machine's Tailscale IPv4."""
import html, os, subprocess, sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs

COUNTRIES = ["New_Zealand", "Australia", "Japan", "United_States", "United_Kingdom", "Germany"]
ACTIONS = set(COUNTRIES) | {"fastest", "disconnect"}
PORT = int(os.environ.get("PORT", "8080"))


def nordvpn(*args):
    r = subprocess.run(["nordvpn", *args], capture_output=True, text=True, timeout=90)
    return (r.stdout + r.stderr).replace("\r", "").strip()


def allowed(choice, origin, host):
    # Origin check stops any random website you visit from POSTing here (Shortcuts sends no Origin).
    if origin and origin.split("://", 1)[-1] != host:
        return False
    return choice in ACTIONS


def page(status):
    buttons = "".join(f'<button name="c" value="{c}">{c.replace("_", " ")}</button>' for c in COUNTRIES)
    return f"""<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>NordVPN</title>
<style>
body{{font:16px system-ui;margin:16px;max-width:480px;background:#fff;color:#111}}
button{{display:block;width:100%;padding:14px;margin:6px 0;font-size:17px;border-radius:10px;border:1px solid #888;background:#f4f4f4;color:inherit}}
pre{{white-space:pre-wrap;background:#eee;padding:10px;border-radius:8px}}
@media (prefers-color-scheme:dark){{body{{background:#111;color:#eee}}pre,button{{background:#222}}}}
</style>
<h1>NordVPN</h1><pre>{html.escape(status)}</pre>
<form method="post"><button name="c" value="fastest">Fastest</button>{buttons}<button name="c" value="disconnect">Disconnect</button></form>
</html>"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/":
            return self.send_error(404)
        body = page(nordvpn("status")).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        length = min(int(self.headers.get("Content-Length") or 0), 1024)
        choice = parse_qs(self.rfile.read(length).decode()).get("c", [""])[0]
        if not allowed(choice, self.headers.get("Origin"), self.headers.get("Host")):
            return self.send_error(403)
        if choice == "disconnect":
            nordvpn("disconnect")
        else:
            nordvpn("connect", *([] if choice == "fastest" else [choice]))
        self.send_response(303)  # redirect so a refresh doesn't resubmit
        self.send_header("Location", "/")
        self.end_headers()


def selftest():
    assert allowed("Japan", None, "x:8080")
    assert allowed("disconnect", "http://x:8080", "x:8080")
    assert allowed("fastest", None, "x:8080")
    assert not allowed("Japan; rm -rf /", None, "x:8080")
    assert not allowed("Japan", "https://evil.example", "x:8080")
    assert "&lt;b&gt;" in page("<b>")
    print("ok")


if __name__ == "__main__":
    if sys.argv[1:] == ["--selftest"]:
        selftest()
        sys.exit()
    ip = subprocess.run(["tailscale", "ip", "-4"], capture_output=True, text=True, check=True).stdout.split()[0]
    print(f"listening on http://{ip}:{PORT}", flush=True)
    ThreadingHTTPServer((ip, PORT), Handler).serve_forever()
