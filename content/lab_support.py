"""Shared simulated lab code used as a supporting file by the pytest lessons (not a lesson module)."""

LAB_PY = '''"""Simulated lab devices so the pytest lessons run without hardware."""


class FakeAP:
    def __init__(self, name, bands=("2G", "5G", "6G")):
        self.name = name
        self.bands = set(bands)
        self.channels = {}
        self.reboots = 0

    def __repr__(self):
        return f"FakeAP({self.name!r})"

    def set_channel(self, band, channel):
        if band not in self.bands:
            raise ValueError(f"{self.name} has no {band} radio")
        self.channels[band] = channel

    def reboot(self):
        self.reboots += 1
        self.channels.clear()


class FakeStation:
    def __init__(self, mac):
        self.mac = mac
        self.ap = None
        self.rssi = None

    def __repr__(self):
        return f"FakeStation({self.mac!r})"

    def associate(self, ap, rssi=-55):
        self.ap, self.rssi = ap, rssi
        return True

    def disconnect(self):
        self.ap = None


MAX_WIDTH = {"2G": 40, "5G": 160, "6G": 320}
PEAK_MBPS = {"2G": 300.0, "5G": 1800.0, "6G": 4800.0}


def throughput_mbps(band, width, rssi=-50):
    """Deterministic stand-in for an iperf3 measurement."""
    if width > MAX_WIDTH[band]:
        raise ValueError(f"{width} MHz not allowed on {band}")
    base = PEAK_MBPS[band] * width / MAX_WIDTH[band]
    penalty = min(0.9, max(0, -rssi - 50) * 0.02)
    return round(base * (1 - penalty), 1)
'''
