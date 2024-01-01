from typing import List
from unittest import mock

import pytest

from gdb_remote_client import GdbRemoteClient


@pytest.fixture
def dut():
    with mock.patch("gdb_remote_client.client.GdbRemoteClientBase") as m:
        yield GdbRemoteClient("localhost", 3333)


def _assert_packet_sent(dut: GdbRemoteClient, pkt: bytes):
    dut._client_base.send_packet.assert_called_once_with(pkt)


def _assert_no_packet_sent(dut: GdbRemoteClient):
    dut._client_base.send_packet.assert_not_called()


def _assert_no_recv_attempted(dut: GdbRemoteClient):
    dut._client_base.recv_and_decode_packet_data.assert_not_called()


def _mock_incoming_packet_data(dut: GdbRemoteClient, pkt_data: List[bytes]):
    dut._client_base.recv_and_decode_packet_data.side_effect = pkt_data


def test_cmd(dut):
    _mock_incoming_packet_data(dut, [b"OK"])
    dut.cmd("qSomething") == "OK"
    _assert_packet_sent(dut, b"qSomething")


def test_cmd_empty_reply(dut):
    _mock_incoming_packet_data(dut, [b""])
    dut.cmd("vMustReplyEmpty") == ""
    _assert_packet_sent(dut, b"vMustReplyEmpty")


def test_cmd_bin_input(dut):
    _mock_incoming_packet_data(dut, [b"OK"])
    dut.cmd(b"qSomethingBinary\x10\xff") == "OK"
    _assert_packet_sent(dut, b"qSomethingBinary\x10\xff")


def test_cmd_bin_output_unexpected(dut):
    _mock_incoming_packet_data(dut, [b"binaryOut\xe0\xf0"])
    with pytest.raises(RuntimeError) as e:
        dut.cmd(b"qSomething")
    assert "Expected ASCII-only response" in str(e.value)
    _assert_packet_sent(dut, b"qSomething")


def test_cmd_bin_reply(dut):
    _mock_incoming_packet_data(dut, [b"binaryOut\xe0\xf0"])
    dut.cmd_bin_reply(b"qSomething") == b"binaryOut\xe0\xf0"
    _assert_packet_sent(dut, b"qSomething")


def test_cmd_no_reply(dut):
    dut.cmd_no_reply(b"vCont;c")
    _assert_packet_sent(dut, b"vCont;c")
    _assert_no_recv_attempted(dut)


def test_cmd_no_reply(dut):
    dut.ctrl_c()
    dut._client_base.send_ctrl_c.assert_called_once()


def test_get_stop_reply_simple(dut):
    _mock_incoming_packet_data(dut, [b"W00"])
    reply, console_out = dut.get_stop_reply()
    assert reply == "W00"
    assert console_out == ""
    _assert_no_packet_sent(dut)


def test_get_stop_reply_complex(dut):
    incoming_data = [
        b"O61206220630a",  # a b c\n
        b"O646566",  # def
        b"T05",
    ]
    _mock_incoming_packet_data(dut, incoming_data)
    reply, console_out = dut.get_stop_reply()
    assert reply == "T05"
    assert console_out == "a b c\ndef"
    _assert_no_packet_sent(dut)
