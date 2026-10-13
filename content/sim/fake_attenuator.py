"""A simulated programmable RF attenuator with an HTTP API in the style of common USB/Ethernet attenuators.

GET /MN?            -> model name
GET /SETATT=<dB>    -> "1" on success, "0" if out of range (0-95 dB, 0.25 dB steps)
GET /ATT?           -> current attenuation, e.g. "30.25"
"""
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

STATE = {"att": 0.0, "history": []}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def text(self, body):
        data = body.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        cmd = self.path.lstrip("/").rstrip("?")  # clients may or may not send the trailing "?"
        if cmd == "MN":
            return self.text("MN=RCDAT-6000-95")
        if cmd == "ATT":
            return self.text(f"{STATE['att']:g}")
        if cmd.startswith("SETATT="):
            try:
                value = float(cmd.split("=", 1)[1])
            except ValueError:
                return self.text("0")
            if not 0 <= value <= 95 or (value * 4) % 1:
                return self.text("0")
            STATE["att"] = value
            STATE["history"].append(value)
            return self.text("1")
        self.send_error(404)


def start():
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{server.server_address[1]}"


def current():
    return STATE["att"]
