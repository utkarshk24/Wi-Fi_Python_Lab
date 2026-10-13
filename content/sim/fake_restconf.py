"""A small RESTCONF server (RFC 8040 style URLs, YANG-JSON bodies) on localhost."""
import base64
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

AUTH = "Basic " + base64.b64encode(b"admin:lab123").decode()
MEDIA = "application/yang-data+json"
INTERFACES = {
    "GigabitEthernet1": {"name": "GigabitEthernet1", "description": "uplink to core", "type": "iana-if-type:ethernetCsmacd", "enabled": True},
    "GigabitEthernet2": {"name": "GigabitEthernet2", "description": "ap-lab-07", "type": "iana-if-type:ethernetCsmacd", "enabled": True},
    "GigabitEthernet3": {"name": "GigabitEthernet3", "description": "", "type": "iana-if-type:ethernetCsmacd", "enabled": False},
}
BASE = "/restconf/data/ietf-interfaces:interfaces"


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def reply(self, status, body=None):
        data = json.dumps(body).encode() if body is not None else b""
        self.send_response(status)
        if body is not None:
            self.send_header("Content-Type", MEDIA)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def checks(self):
        if self.headers.get("Authorization") != AUTH:
            self.reply(401, {"ietf-restconf:errors": {"error": [{"error-tag": "access-denied"}]}})
            return False
        if MEDIA not in (self.headers.get("Accept") or "") and self.command == "GET":
            self.reply(406, {"ietf-restconf:errors": {"error": [{"error-tag": "operation-not-supported"}]}})
            return False
        return True

    def target(self):
        if self.path.rstrip("/") == BASE:
            return "all", None
        prefix = BASE + "/interface="
        if self.path.startswith(prefix):
            return "one", self.path[len(prefix):].replace("%2F", "/")
        return None, None

    def do_GET(self):
        if not self.checks():
            return
        kind, name = self.target()
        if kind == "all":
            return self.reply(200, {"ietf-interfaces:interfaces": {"interface": list(INTERFACES.values())}})
        if kind == "one" and name in INTERFACES:
            return self.reply(200, {"ietf-interfaces:interface": [INTERFACES[name]]})
        return self.reply(404, {"ietf-restconf:errors": {"error": [{"error-tag": "invalid-value", "error-message": "uri keypath not found"}]}})

    def do_PATCH(self):
        if not self.checks():
            return
        kind, name = self.target()
        if kind != "one" or name not in INTERFACES:
            return self.reply(404, {"ietf-restconf:errors": {"error": [{"error-tag": "invalid-value"}]}})
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        INTERFACES[name].update(body["ietf-interfaces:interface"][0])
        return self.reply(204)


def start():
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{server.server_address[1]}"
