"""A minimal HashiCorp Vault KV v2 endpoint: GET /v1/secret/data/<path> with an X-Vault-Token header."""
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

TOKEN = "hvs.lab-ci-readonly"
SECRETS = {
    "lab/bench07": {"ssh_user": "admin", "ssh_password": "Wl@n-7-s3cret", "snmp_community": "lab7-ro"},
    "lab/lanforge": {"api_token": "lf-0f9e8d7c6b5a"},
}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def reply(self, status, body):
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.headers.get("X-Vault-Token") != TOKEN:
            return self.reply(403, {"errors": ["permission denied"]})
        prefix = "/v1/secret/data/"
        if not self.path.startswith(prefix):
            return self.reply(404, {"errors": []})
        path = self.path[len(prefix):]
        if not path.startswith("lab/"):
            return self.reply(403, {"errors": ["permission denied"]})  # this token's policy only covers lab/*
        if path not in SECRETS:
            return self.reply(404, {"errors": []})
        return self.reply(200, {"data": {"data": SECRETS[path], "metadata": {"version": 3, "created_time": "2026-09-30T08:00:00Z"}},
                                "lease_duration": 0, "renewable": False})


def start():
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{server.server_address[1]}"
