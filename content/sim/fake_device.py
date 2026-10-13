"""Simulated network devices reachable over real SSH on localhost (paramiko server).

Supports exec commands, an interactive IOS-like shell with config mode, and a minimal
NETCONF 1.0 subsystem, so Paramiko, Netmiko, asyncssh, Nornir and ncclient all work.
"""
import re
import socket
import threading
import time

import paramiko

USER, PASSWORD = "admin", "lab123"
HOST_KEY = paramiko.RSAKey.generate(2048)

SHOW = {
    "show version": "Cisco IOS XE Software, Version 17.9.4a\n{host} uptime is 3 weeks, 2 days\ncisco C9800-L (X86_64) processor\n",
    "show ip interface brief": (
        "Interface              IP-Address      OK? Method Status                Protocol\n"
        "GigabitEthernet0/0/0   {ip_a:<15} YES NVRAM  up                    up\n"
        "GigabitEthernet0/0/1   unassigned      YES unset  administratively down down\n"
        "Vlan100                {ip_b:<15} YES NVRAM  up                    up\n"
    ),
    "show ap summary": (
        "Number of APs: 3\n\n"
        "AP Name       Slots  AP Model          Ethernet MAC    Radio MAC       Location   IP Address     State\n"
        "--------------------------------------------------------------------------------------------------------\n"
        "ap-lab-07     3      CW9166I-B         3c84.6a12.3456  3c84.6a12.3460  lab-7      10.10.30.7     Registered\n"
        "ap-lab-08     3      CW9166I-B         3c84.6a12.3478  3c84.6a12.3480  lab-8      10.10.30.8     Registered\n"
        "ap-lab-09     2      C9120AXI-B        3c84.6a12.34a0  3c84.6a12.34b0  lab-9      10.10.30.9     Downloading\n"
    ),
    "show clock": "*10:15:02.118 UTC Mon Oct 12 2026\n",
    "show wireless client summary": (
        "Number of Clients: 3\n\n"
        "MAC Address    AP Name         Type ID   State             Protocol Method     Role\n"
        "-------------------------------------------------------------------------------------\n"
        "0a1b.2c3d.4e01 ap-lab-07       WLAN 1    Run               11ax(6)  None       Local\n"
        "0a1b.2c3d.4e02 ap-lab-07       WLAN 1    Run               11ax(5)  None       Local\n"
        "0a1b.2c3d.4e03 ap-lab-08       WLAN 2    Authenticating    11ac     Dot1x      Local\n"
    ),
    "write memory": "Building configuration...\n[OK]\n",
    "write mem": "Building configuration...\n[OK]\n",
    "terminal length 0": "",
    "terminal width 511": "",
}


class Server(paramiko.ServerInterface):
    def __init__(self):
        self.event = threading.Event()
        self.kind = None
        self.command = None

    def check_auth_password(self, username, password):
        ok = (username, password) == (USER, PASSWORD)
        return paramiko.AUTH_SUCCESSFUL if ok else paramiko.AUTH_FAILED

    def get_allowed_auths(self, username):
        return "password"

    def check_channel_request(self, kind, chanid):
        return paramiko.OPEN_SUCCEEDED if kind == "session" else paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_channel_pty_request(self, *args):
        return True

    def check_channel_shell_request(self, channel):
        self.kind = "shell"
        self.event.set()
        return True

    def check_channel_subsystem_request(self, channel, name):
        if name != "netconf":
            return False
        self.kind = "netconf"
        self.event.set()
        return True

    def check_channel_exec_request(self, channel, command):
        self.kind, self.command = "exec", command.decode()
        self.event.set()
        return True


class Device:
    def __init__(self, host, n):
        self.host, self.n = host, n
        self.running_config = ["hostname " + host, "interface Vlan100", " description mgmt"]
        self.nc_interfaces = {"GigabitEthernet1": ["uplink to core", "true"], "GigabitEthernet2": ["ap-lab-07", "true"],
                              "GigabitEthernet3": ["", "false"]}

    def run(self, cmd, mode):
        cmd = cmd.strip()
        if not cmd:
            return "", mode
        if cmd == "show tech-support wireless":
            time.sleep(1)
            return f"----- show tech-support wireless ({self.host}) -----\n... 1,842 lines ...\n", mode
        if cmd in SHOW:
            return SHOW[cmd].format(host=self.host, ip_a=f"10.10.20.{self.n}", ip_b=f"192.168.100.{self.n}"), mode
        if cmd == "show running-config":
            return "\n".join(["Building configuration...", ""] + self.running_config + ["end"]) + "\n", mode
        if cmd in ("configure terminal", "conf t") and mode == "#":
            return "Enter configuration commands, one per line.  End with CNTL/Z.\n", "(config)#"
        if mode.startswith("(config") and cmd in ("end", "exit"):
            return "", "#"
        if mode.startswith("(config"):
            if cmd.startswith("interface "):
                self.running_config.append(cmd)
                return "", "(config-if)#"
            self.running_config.append((" " if mode == "(config-if)#" else "") + cmd)
            return "", mode
        if not cmd:
            return "", mode
        return f"                ^\n% Invalid input detected at '^' marker.\n", mode


NC_END = b"]]>]]>"
NC_HELLO = ('<?xml version="1.0" encoding="UTF-8"?><hello xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">'
            "<capabilities><capability>urn:ietf:params:netconf:base:1.0</capability>"
            "<capability>urn:ietf:params:netconf:capability:candidate:1.0</capability>"
            "<capability>urn:ietf:params:xml:ns:yang:ietf-interfaces?module=ietf-interfaces&amp;revision=2014-05-08</capability>"
            "</capabilities><session-id>4242</session-id></hello>")


def _nc_interfaces(device, only=()):
    rows = "".join(f"<interface><name>{n}</name><description>{d}</description><enabled>{e}</enabled></interface>"
                   for n, (d, e) in device.nc_interfaces.items() if not only or n in only)
    return f'<interfaces xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces">{rows}</interfaces>'


def _netconf(chan, device):
    chan.sendall(NC_HELLO.encode() + NC_END)
    buf = b""
    while True:
        data = chan.recv(65535)
        if not data:
            return
        buf += data
        while NC_END in buf:
            msg, buf = buf.split(NC_END, 1)
            text = msg.decode()
            if re.search(r"<(\w+:)?hello[ >]", text):
                continue
            mid = re.search(r'message-id="([^"]+)"', text)
            mid = mid.group(1) if mid else "0"
            if re.search(r"<(\w+:)?get(-config)?[ />]", text):
                body = f"<data>{_nc_interfaces(device, re.findall(r'<name>([^<]+)</name>', text))}</data>"
            elif "edit-config" in text:
                for name, desc in re.findall(r"<name>([^<]+)</name>\s*<description>([^<]*)</description>", text):
                    device.nc_interfaces.setdefault(name, ["", "true"])[0] = desc
                body = "<ok/>"
            elif "close-session" in text:
                chan.sendall(f'<rpc-reply xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="{mid}"><ok/></rpc-reply>'.encode() + NC_END)
                chan.close()
                return
            else:
                body = ("<rpc-error><error-type>protocol</error-type><error-tag>operation-not-supported</error-tag>"
                        "<error-severity>error</error-severity></rpc-error>")
            reply = f'<rpc-reply xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="{mid}">{body}</rpc-reply>'
            chan.sendall(reply.encode() + NC_END)


def _handle(client, device):
    try:
        _session(client, device)
    except (EOFError, OSError, paramiko.SSHException):
        pass  # client went away mid-session: normal for a lab device


def _session(client, device):
    transport = paramiko.Transport(client)
    transport.add_server_key(HOST_KEY)
    server = Server()
    try:
        transport.start_server(server=server)
    except Exception:
        return
    while transport.is_active():
        chan = transport.accept(5)
        if chan is None:
            continue
        server.event.wait(5)
        if server.kind == "netconf":
            _netconf(chan, device)
            _wait_for_client(transport)
            break
        if server.kind == "exec":
            out, _ = device.run(server.command, "#")
            bad = "Invalid input" in out
            chan.sendall(out.replace("\n", "\r\n").encode())
            chan.send_exit_status(1 if bad else 0)
            chan.close()
            server.event.clear()
            continue
        mode = "#"
        chan.sendall(f"\r\n{device.host}{mode}".encode())
        buf = b""
        while True:
            data = chan.recv(1024)
            if not data:
                break
            buf += data
            while b"\r" in buf or b"\n" in buf:
                idx = min(i for i in (buf.find(b"\r"), buf.find(b"\n")) if i >= 0)
                line, buf = buf[:idx], buf[idx + 1:].lstrip(b"\n")
                cmd = line.decode(errors="replace")
                if cmd.strip() in ("exit", "logout") and mode == "#":
                    chan.sendall(cmd.encode() + b"\r\n")
                    chan.close()
                    return
                out, mode = device.run(cmd, mode)
                chan.sendall(cmd.encode() + b"\r\n" + out.replace("\n", "\r\n").encode() + f"{device.host}{mode}".encode())
        break


def _wait_for_client(transport, limit=5.0):
    """Let the client close the connection first, as real devices do."""
    deadline = time.monotonic() + limit
    while transport.is_active() and time.monotonic() < deadline:
        time.sleep(0.05)


def start(host="core-sw-1", n=1):
    """Start one simulated device; returns its TCP port on 127.0.0.1."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("127.0.0.1", 0))
    sock.listen(20)
    device = Device(host, n)

    def accept_loop():
        while True:
            client, _ = sock.accept()
            threading.Thread(target=_handle, args=(client, device), daemon=True).start()

    threading.Thread(target=accept_loop, daemon=True).start()
    return sock.getsockname()[1]
