# SPDX-License-Identifier: MIT

import pytest

from gdb_remote_client import PacketFormatError
from gdb_remote_client.utils import (
    ascii_from_hex,
    compute_checksum,
    create_packet,
    decode_packet_data,
    encode_packet_data,
    split_packet,
    validate_packet,
)


def test_decode_packet_data_plain():
    assert decode_packet_data(b"") == b""
    assert decode_packet_data(b"abc") == b"abc"
    assert decode_packet_data(b"def\x8f") == b"def\x8f"


def test_decode_packet_data_escape():
    assert decode_packet_data(b"jkl}d") == b"jklD"
    assert decode_packet_data(b"abc}ddef") == b"abcDdef"
    assert decode_packet_data(b"}\x03") == b"#"
    assert decode_packet_data(b"}\x04") == b"$"
    assert decode_packet_data(b"}\x0a") == b"*"
    assert decode_packet_data(b"}]") == b"}"

    with pytest.raises(PacketFormatError) as e:
        decode_packet_data(b"abc}")
    assert "Missing one more character after }" in str(e.value)


def test_decode_packet_data_run_length():
    assert decode_packet_data(b"a* ") == b"aaaa"
    assert decode_packet_data(b"EFGa*!HIJ") == b"EFGaaaaaHIJ"

    with pytest.raises(PacketFormatError) as e:
        decode_packet_data(b"pqr*")
    assert "Missing one more character after *" in str(e.value)

    with pytest.raises(PacketFormatError) as e:
        decode_packet_data(b"a*#")
    assert "Bytes # or $ cannot be used" in str(e.value)

    with pytest.raises(PacketFormatError) as e:
        decode_packet_data(b"a*$")
    assert "Bytes # or $ cannot be used" in str(e.value)

    with pytest.raises(PacketFormatError) as e:
        decode_packet_data(b"a*\x1f")
    assert "repetiton byte must be in range 32 - 126" in str(e.value)

    with pytest.raises(PacketFormatError) as e:
        decode_packet_data(b"a*\x7f")
    assert "repetiton byte must be in range 32 - 126" in str(e.value)


def test_encode_packet_data():
    assert encode_packet_data(b"") == b""
    assert encode_packet_data(b"abc") == b"abc"
    assert encode_packet_data(b"}$#*") == b"}]}\x04}\x03*"


def test_compute_checksum():
    assert compute_checksum(b"") == b"00"
    assert compute_checksum(b" ") == b"20"
    assert compute_checksum(b"\x40\x40") == b"80"
    assert compute_checksum(b"abc") == b"26"


def test_create_packet():
    assert create_packet(b"") == b"$#00"
    assert create_packet(b"abc") == b"$abc#26"
    assert create_packet(b"abc", custom_checksum=b"11") == b"$abc#11"

    with pytest.raises(ValueError) as e:
        create_packet(b"abc", custom_checksum=b"xx")
    assert "expected two hex digits" in str(e.value)

    with pytest.raises(ValueError) as e:
        create_packet(b"abc", custom_checksum=b"2")
    assert "expected two hex digits" in str(e.value)

    with pytest.raises(ValueError) as e:
        create_packet(b"abc", custom_checksum=b"def")
    assert "expected two hex digits" in str(e.value)


def test_split_packet():
    assert split_packet(b"#$00") == (b"#", b"", b"$", b"00")
    assert split_packet(b"#abc$26") == (b"#", b"abc", b"$", b"26")


def test_validate_packet():
    with pytest.raises(PacketFormatError) as e:
        validate_packet(b"$a#")
    assert "Too short" in str(e.value)

    with pytest.raises(PacketFormatError) as e:
        validate_packet(b"a#00")
    assert "Expected first packet byte to be $" in str(e.value)

    with pytest.raises(PacketFormatError) as e:
        validate_packet(b"$b00")
    assert "Expected # character before the checksum" in str(e.value)

    with pytest.raises(PacketFormatError) as e:
        validate_packet(b"$##ab")
    assert "Found special character #" in str(e.value)

    with pytest.raises(PacketFormatError) as e:
        validate_packet(b"$$#cd")
    assert "Found special character $" in str(e.value)

    with pytest.raises(PacketFormatError) as e:
        validate_packet(b"$#xx")
    assert "Received checksum has incorrect syntax" in str(e.value)

    with pytest.raises(PacketFormatError) as e:
        validate_packet(b"$#01")
    assert "Packet has invalid checksum" in str(e.value)

    validate_packet(b"$#00")
    validate_packet(b"$abc#26")


def test_ascii_from_hex():
    assert ascii_from_hex("20616263") == " abc"
    with pytest.raises(ValueError) as e:
        ascii_from_hex("202")
    assert "Expected even number" in str(e.value)
