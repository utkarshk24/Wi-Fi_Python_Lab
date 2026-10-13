"""A small Jenkins-like REST API: trigger a parameterized job, follow the queue item, poll the build, read the test report."""
import base64
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

AUTH = "Basic " + base64.b64encode(b"ci-bot:11a2b3c4d5e6f7a8b9c0").decode()
STATE = {"queue": {}, "builds": {}, "next_queue": 101, "next_build": 42}
REPORT = {
    "passCount": 41, "failCount": 2, "skipCount": 1,
    "suites": [{"name": "tests.test_rvr", "cases": [
        {"className": "tests.test_rvr", "name": "test_rvr_point[5G-42dB]", "status": "FAILED",
         "errorDetails": "AssertionError: 5G at 42 dB: 135.9 Mbps < KPI 150"},
        {"className": "tests.test_roam", "name": "test_11r_roam_time", "status": "REGRESSION",
         "errorDetails": "AssertionError: roam took 182 ms (limit 50 ms)"},
        {"className": "tests.test_rvr", "name": "test_rvr_point[6G-0dB]", "status": "PASSED", "errorDetails": None},
    ]}],
}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def reply(self, status, body=None, headers=None):
        data = json.dumps(body).encode() if body is not None else b""
        self.send_response(status)
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        if body is not None:
            self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def authorized(self):
        if self.headers.get("Authorization") != AUTH:
            self.reply(401, {"message": "Authentication required"})
            return False
        return True

    def do_POST(self):
        if not self.authorized():
            return
        url = urlparse(self.path)
        parts = url.path.strip("/").split("/")
        if len(parts) == 3 and parts[0] == "job" and parts[2] == "buildWithParameters":
            qid = STATE["next_queue"]
            STATE["next_queue"] += 1
            params = {k: v[0] for k, v in parse_qs(url.query).items()}
            STATE["queue"][qid] = {"job": parts[1], "params": params, "polls": 0}
            host = self.headers.get("Host")
            return self.reply(201, None, {"Location": f"http://{host}/queue/item/{qid}/"})
        return self.reply(404, {"message": "not found"})

    def do_GET(self):
        if not self.authorized():
            return
        parts = urlparse(self.path).path.strip("/").split("/")
        if parts[:2] == ["queue", "item"]:
            item = STATE["queue"].get(int(parts[2]))
            if not item:
                return self.reply(404, {"message": "no such queue item"})
            item["polls"] += 1
            if item["polls"] < 3:
                return self.reply(200, {"id": int(parts[2]), "why": "Waiting for next available executor on 'wifi-bench'", "executable": None})
            if "build" not in item:
                item["build"] = STATE["next_build"]
                STATE["next_build"] += 1
                STATE["builds"][(item["job"], item["build"])] = {"polls": 0, "params": item["params"]}
            host = self.headers.get("Host")
            return self.reply(200, {"id": int(parts[2]), "why": None, "executable": {"number": item["build"], "url": f"http://{host}/job/{item['job']}/{item['build']}/"}})
        if parts[0] == "job" and len(parts) >= 4 and parts[2].isdigit():
            build = STATE["builds"].get((parts[1], int(parts[2])))
            if not build:
                return self.reply(404, {"message": "no such build"})
            if parts[3:5] == ["testReport", "api"]:
                return self.reply(200, REPORT)
            build["polls"] += 1
            done = build["polls"] >= 3
            return self.reply(200, {"number": int(parts[2]), "building": not done, "result": "UNSTABLE" if done else None,
                                    "duration": 512000 if done else 0,
                                    "actions": [{"parameters": [{"name": k, "value": v} for k, v in build["params"].items()]}]})
        return self.reply(404, {"message": "not found"})


def start():
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{server.server_address[1]}"
