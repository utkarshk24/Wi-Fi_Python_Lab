"""A simulated LANforge-style JSON API: stations (ports) and layer-3 traffic endpoints.

Throughput depends on the attenuation reported by fake_attenuator (if it's running in this process),
so rate-vs-range sweeps produce a realistic curve.
"""
import json
import math
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORTS = {"1.1.wlan0": {"alias": "wlan0", "phantom": False, "down": False, "ip": "0.0.0.0", "ap": "NA", "signal": "0 dBm", "mode": "802.11ax"}}
CX = {}
PEAK = {"5G": 940.0, "6G": 2410.0, "2G": 280.0}


def _atten():
    try:
        import fake_attenuator
        return fake_attenuator.current()
    except ImportError:
        return 0.0


def _rate(band):
    att = _atten()
    knee = {"2G": 38, "5G": 34, "6G": 30}[band]
    frac = 1 / (1 + math.exp((att - knee) / 4.5))
    return round(PEAK[band] * frac, 1)


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
        parts = self.path.strip("/").split("/")
        if parts[0] == "port" and len(parts) == 4:
            key = ".".join(parts[1:])
            if key in PORTS:
                port = dict(PORTS[key])
                if not port["down"] and time.monotonic() - port.get("up_at", 0) < 0.3:
                    port.update(ip="0.0.0.0", ap="NA")
                port.pop("up_at", None)
                if port["ip"] != "0.0.0.0":
                    port["signal"] = f"{-38 - round(_atten())} dBm"
                return self.reply(200, {"interface": port})
            return self.reply(404, {"errors": [f"no port {key}"]})
        if parts[0] == "cx" and len(parts) == 2:
            name = parts[1]
            if name not in CX:
                return self.reply(404, {"errors": [f"no cross-connect {name}"]})
            cx = CX[name]
            rate = _rate(cx["band"]) if cx["state"] == "Run" else 0.0
            return self.reply(200, {name: {"state": cx["state"], "bps rx a": int(rate * 1e6 * 0.02), "bps rx b": int(rate * 1e6)}})
        return self.reply(404, {"errors": ["unknown path"]})

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])) or b"{}")
        cmd = self.path.strip("/")
        if cmd == "cli-json/add_sta":
            key = f"1.{body['resource']}.{body['sta_name']}"
            PORTS[key] = {"alias": body["sta_name"], "phantom": False, "down": True, "ip": "0.0.0.0", "ap": "NA",
                          "signal": "0 dBm", "mode": body.get("mode", "802.11ax"), "ssid": body["ssid"]}
            return self.reply(200, {"status": "OK"})
        if cmd == "cli-json/set_port":
            key = f"1.{body['resource']}.{body['port']}"
            if key not in PORTS:
                return self.reply(404, {"errors": [f"no port {key}"]})
            up = body.get("current_flags", 0) == 0
            PORTS[key].update(down=not up, ip="192.168.100.57" if up else "0.0.0.0", ap="3c:84:6a:12:34:60" if up else "NA",
                              up_at=time.monotonic())
            return self.reply(200, {"status": "OK"})
        if cmd == "cli-json/add_cx":
            CX[body["alias"]] = {"state": "Stopped", "band": body.get("band", "5G")}
            return self.reply(200, {"status": "OK"})
        if cmd == "cli-json/set_cx_state":
            if body["cx_name"] not in CX:
                return self.reply(404, {"errors": ["no such cx"]})
            CX[body["cx_name"]]["state"] = "Run" if body["cx_state"] == "RUNNING" else "Stopped"
            return self.reply(200, {"status": "OK"})
        return self.reply(404, {"errors": ["unknown command"]})


def start():
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{server.server_address[1]}"
