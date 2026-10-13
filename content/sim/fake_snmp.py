"""A tiny SNMPv2c agent (get, getnext, getbulk) built with scapy's SNMP layer, on a UDP port on localhost."""
import socket
import threading

from scapy.asn1.asn1 import ASN1_INTEGER, ASN1_OID, ASN1_STRING, ASN1_TIME_TICKS, ASN1_COUNTER32
from scapy.layers.snmp import SNMP, SNMPresponse, SNMPvarbind

COMMUNITY = b"public"
MIB = {
    "1.3.6.1.2.1.1.1.0": ASN1_STRING(b"AP-OS 7.4.1 CW9166I"),
    "1.3.6.1.2.1.1.3.0": ASN1_TIME_TICKS(26784300),
    "1.3.6.1.2.1.1.5.0": ASN1_STRING(b"ap-lab-07"),
    "1.3.6.1.2.1.1.6.0": ASN1_STRING(b"Lab 7, rack B"),
    "1.3.6.1.2.1.2.2.1.2.1": ASN1_STRING(b"eth0"),
    "1.3.6.1.2.1.2.2.1.2.2": ASN1_STRING(b"wlan0"),
    "1.3.6.1.2.1.2.2.1.2.3": ASN1_STRING(b"wlan1"),
    "1.3.6.1.2.1.2.2.1.8.1": ASN1_INTEGER(1),
    "1.3.6.1.2.1.2.2.1.8.2": ASN1_INTEGER(1),
    "1.3.6.1.2.1.2.2.1.8.3": ASN1_INTEGER(2),
    "1.3.6.1.2.1.4.1.0": ASN1_INTEGER(2),
}
COUNTERS = {  # ifInOctets per interface: start value, bytes added per poll
    "1.3.6.1.2.1.2.2.1.10.1": [918273645, 1_250_000],
    "1.3.6.1.2.1.2.2.1.10.2": [4294000000, 31_250_000],
    "1.3.6.1.2.1.2.2.1.10.3": [0, 0],
}
for _oid in COUNTERS:
    MIB[_oid] = None


def _value(oid):
    if oid in COUNTERS:
        value, step = COUNTERS[oid]
        COUNTERS[oid][0] = (value + step) % 2**32
        return ASN1_COUNTER32(value)
    return MIB[oid]


def _key(oid):
    return tuple(int(x) for x in oid.split("."))


ORDER = sorted(MIB, key=_key)


def _next(oid):
    for o in ORDER:
        if _key(o) > _key(oid):
            return o
    return None


def _serve(sock):
    while True:
        data, addr = sock.recvfrom(65535)
        try:
            req = SNMP(data)
        except Exception:
            continue
        if req.community.val != COMMUNITY:
            continue
        pdu = req.PDU
        kind = pdu.__class__.__name__
        binds = []
        if kind == "SNMPbulk":
            oid = pdu.varbindlist[0].oid.val
            for _ in range(int(pdu.max_repetitions.val)):
                oid = _next(oid)
                if oid is None:
                    break
                binds.append(SNMPvarbind(oid=ASN1_OID(oid), value=_value(oid)))
        else:
            for vb in pdu.varbindlist:
                oid = vb.oid.val
                target = oid if kind == "SNMPget" else _next(oid)
                if target in MIB:
                    binds.append(SNMPvarbind(oid=ASN1_OID(target), value=_value(target)))
                else:
                    binds.append(SNMPvarbind(oid=ASN1_OID(oid), value=ASN1_STRING(b""), ))
        resp = SNMP(version=req.version, community=req.community,
                    PDU=SNMPresponse(id=pdu.id, varbindlist=binds))
        sock.sendto(bytes(resp), addr)


def start():
    """Start the agent; returns its UDP port on 127.0.0.1."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", 0))
    threading.Thread(target=_serve, args=(sock,), daemon=True).start()
    return sock.getsockname()[1]
