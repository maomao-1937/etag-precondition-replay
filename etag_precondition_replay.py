"""Replay origin If-Match and If-None-Match decisions from a local fixture."""

import json
import os
import posixpath
import re
import stat
import sys


MAX_BYTES = 256 * 1024
MAX_HEADER = 8192
MAX_SLOTS = 128
FIELDS = {"method", "exists", "etag", "if_match", "if_none_match"}
METHOD = re.compile(r"[A-Za-z0-9!#$%&'*+.^_\x60|~-]{1,64}")
ENTITY_TAG = re.compile(r'(W/)?"([\x21\x23-\x7e\x80-\xff]*)"')
OWS = re.compile(r"[ \t]*")
DEVICE = re.compile(r"CON|PRN|AUX|NUL|CONIN\$|CONOUT\$|(?:COM|LPT)[0-9¹²³]")
NATIVE_ROOTS = {"??", "device", "dosdevices", "global??", "systemroot", "globalroot"}


def check_path(path):
    spelling = path.replace("\\", "/")
    if not spelling or spelling == "-" or spelling.startswith("//") or spelling.endswith("/"):
        raise ValueError
    if any(ord(char) < 32 for char in spelling):
        raise ValueError
    if spelling.startswith("/"):
        for version in (spelling, posixpath.normpath(spelling)):
            root = version[1:].partition("/")[0].rstrip(" .").lower()
            if root in NATIVE_ROOTS:
                raise ValueError
    tail = spelling[2:] if re.match(r"^[A-Za-z]:/", spelling) else spelling
    if ":" in tail:
        raise ValueError
    for part in tail.split("/"):
        if part in {"", ".", ".."}:
            continue
        stem = part.partition(".")[0].rstrip(" ").upper()
        if part.endswith((" ", ".")) or DEVICE.fullmatch(stem):
            raise ValueError


def check_file(info):
    if not stat.S_ISREG(info.st_mode) or not 0 <= info.st_size <= MAX_BYTES:
        raise ValueError


def read_input(path):
    check_path(path)
    check_file(os.stat(path))
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NONBLOCK", 0)
    descriptor = os.open(path, flags)
    try:
        check_file(os.fstat(descriptor))
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            data = stream.read(MAX_BYTES + 1)
    finally:
        os.close(descriptor)
    if len(data) > MAX_BYTES:
        raise ValueError
    return data


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError
        result[key] = value
    return result


def reject_number(_value):
    raise ValueError


def header(value):
    if value is None:
        return None
    if not isinstance(value, str) or len(value) > MAX_HEADER:
        raise ValueError
    return value.strip(" \t")


def parse_conditions(value):
    if value is None or value == "*":
        return value
    tags = []
    index = 0
    for _ in range(MAX_SLOTS):
        index = OWS.match(value, index).end()
        if index < len(value) and value[index] != ",":
            tag = ENTITY_TAG.match(value, index)
            if tag is None:
                raise ValueError
            tags.append((bool(tag[1]), tag[2]))
            index = OWS.match(value, tag.end()).end()
        if index == len(value):
            return tags
        if value[index] != ",":
            raise ValueError
        index += 1
    raise ValueError


def matches(condition, current, exists, strong):
    if condition == "*":
        return exists
    if current is None:
        return False
    weak_current, opaque_current = current
    return any(
        opaque_current == opaque and (not strong or not (weak_current or weak_tag))
        for weak_tag, opaque in condition
    )


def decision(http_status=None, field=None):
    return {
        "status": "short_circuit" if http_status is not None else "continue",
        "http_status": http_status,
        "precondition": field,
    }


def replay(document):
    if not isinstance(document, dict) or document.keys() != FIELDS:
        raise ValueError
    method = document["method"]
    exists = document["exists"]
    if not isinstance(method, str) or not METHOD.fullmatch(method) or type(exists) is not bool:
        raise ValueError
    current = None
    saved_etag = header(document["etag"])
    if saved_etag is not None:
        tag = ENTITY_TAG.fullmatch(saved_etag)
        if tag is None or not exists:
            raise ValueError
        current = bool(tag[1]), tag[2]
    if_match = parse_conditions(header(document["if_match"]))
    if_none_match = parse_conditions(header(document["if_none_match"]))
    if if_match is not None and not matches(if_match, current, exists, strong=True):
        return decision(412, "if_match")
    if if_none_match is not None and matches(if_none_match, current, exists, strong=False):
        return decision(304 if method in {"GET", "HEAD"} else 412, "if_none_match")
    return decision()


def emit(data, code):
    remaining = memoryview(data)
    try:
        while remaining:
            written = os.write(1, remaining)
            if written <= 0:
                return 2
            remaining = remaining[written:]
    except OSError:
        return 2
    return code


def main(args):
    if args in (["--help"], ["-h"]):
        return emit(b"Usage: python etag_precondition_replay.py INPUT.json\n", 0)
    try:
        path, = args
        fixture = json.loads(
            read_input(path).decode("utf-8"), object_pairs_hook=unique_object,
            parse_int=reject_number, parse_float=reject_number, parse_constant=reject_number,
        )
        result = replay(fixture)
        code = int(result["status"] == "short_circuit")
    except (OSError, ValueError, RecursionError):
        result, code = {"status": "invalid"}, 2
    return emit(json.dumps(result, separators=(",", ":")).encode("ascii") + b"\n", code)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
