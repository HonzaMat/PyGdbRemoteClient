# SPDX-License-Identifier: MIT

import string
from typing import Optional, Tuple

from .errors import PacketFormatError


def decode_packet_data(data: bytes) -> bytes:
    result = b""
    pos = 0
    while pos < len(data):
        # Peek at the next three bytes.
        c = data[pos : pos + 3]

        if c[0:1] == b"}":
            # Un-escape the next byte.
            if c[1:2] == b"":
                raise PacketFormatError("Missing one more character after }")
            result += _unescape_byte(c[1:2])
            pos += 2
        elif c[1:2] == b"*":
            # Decode run length sequence.
            if len(c) < 3:
                raise PacketFormatError(
                    "Invalid run-length sequence: Missing one more character after *"
                )
            result += _expand_run_length_sequence(c)
            pos += 3
        else:
            # Ordinary byte - copy it as is.
            result += c[0:1]
            pos += 1

    return result


def encode_packet_data(data: bytes) -> bytes:
    result = b""
    for pos in range(len(data)):
        c = data[pos : pos + 1]
        if _needs_escape(c):
            result += b"}" + _escape_byte(c)
        else:
            result += c
    return result


def _needs_escape(c: bytes) -> bool:
    assert len(c) == 1
    return c in b"}$#"


def _escape_byte(c: bytes) -> bytes:
    assert len(c) == 1
    return chr(c[0] ^ 0x20).encode("ascii")


def _unescape_byte(c: bytes) -> bytes:
    return _escape_byte(c)


def _expand_run_length_sequence(seq: bytes) -> bytes:
    assert len(seq) == 3
    assert seq[1:2] == b"*"

    orig_byte = seq[0:1]
    repetition_byte = seq[2:3]

    if repetition_byte in b"#$":
        raise PacketFormatError(
            "Invalid run-length sequence: "
            "Bytes # or $ cannot be used for repetition count"
        )
    if not (32 <= ord(repetition_byte) <= 126):
        raise PacketFormatError(
            "Invalid run-length sequence: The ASCII code of the run-length "
            "repetiton byte must be in range 32 - 126"
        )

    repetition_count = ord(repetition_byte) - 28
    return orig_byte * repetition_count


def compute_checksum(packet_data: bytes) -> bytes:
    checksum_val = sum(b for b in packet_data) % 256
    checksum_bytes = bytes("{:02x}".format(checksum_val), "ascii")
    return checksum_bytes


def _check_checksum_syntax(checksum: bytes) -> bool:
    if len(checksum) != 2:
        return False

    def is_hex_char(c: int) -> bool:
        hexdigits = bytes(string.hexdigits, "ascii")
        return c in hexdigits

    return all(is_hex_char(c) for c in checksum)


def create_packet(packet_data: bytes, custom_checksum: Optional[bytes] = None) -> bytes:
    if custom_checksum is not None:
        if not _check_checksum_syntax(custom_checksum):
            raise ValueError("Invalid checksum, expected two hex digits")

    packet_data_encoded = encode_packet_data(packet_data)
    result = b"$" + packet_data_encoded + b"#"
    if custom_checksum is not None:
        checksum = custom_checksum
    else:
        checksum = compute_checksum(packet_data_encoded)
    result += checksum
    return result


def split_packet(packet: bytes) -> Tuple[bytes, bytes, bytes, bytes]:
    first_char = packet[0:1]
    packet_data = packet[1:-3]
    hash_char = packet[-3:-2]
    checksum = packet[-2:]
    return first_char, packet_data, hash_char, checksum


def validate_packet(packet: bytes) -> None:
    first_char, packet_data, hash_char, checksum = split_packet(packet)

    if len(packet) < 4:
        raise PacketFormatError(
            "Too short packet to be valid, expected at least 4 bytes"
        )

    if first_char != b"$":
        raise PacketFormatError(
            "Expected first packet byte to be $, found " + repr(first_char)
        )

    if hash_char != b"#":
        raise PacketFormatError(
            "Expected # character before the checksum, found " + repr(hash_char)
        )

    # Should not happen, but kept here for extra safety:
    if b"$" in packet_data:
        raise PacketFormatError("Found special character $ in packet data")
    if b"#" in packet_data:
        raise PacketFormatError("Found special character # in packet data")

    if not _check_checksum_syntax(checksum):
        raise PacketFormatError(
            "Received checksum has incorrect syntax. "
            + "Expected two hex digits, found: "
            + repr(checksum)
        )

    checksum_expected = compute_checksum(packet_data)
    if checksum != checksum_expected:
        raise PacketFormatError(
            "Packet has invalid checksum. Expected "
            + repr(checksum_expected)
            + ", found "
            + repr(checksum)
            + "."
        )


def ascii_from_hex(hex_digits: str) -> str:
    if len(hex_digits) % 2 != 0:
        raise ValueError("Expected even number (whole pairs) of hex digits")
    return bytes.fromhex(hex_digits).decode("ascii")
