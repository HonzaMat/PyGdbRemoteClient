# SPDX-License-Identifier: MIT

from unittest import mock

import pytest

from gdb_remote_client import GdbRemoteClientBase, ProtocolError, RecvTimeoutError


@pytest.fixture(autouse=True)
def socket_mock():
    with mock.patch("socket.socket") as m:
        yield m


@pytest.fixture
def dut_unconnected():
    return GdbRemoteClientBase("localhost", 3333)


@pytest.fixture
def dut():
    inst = GdbRemoteClientBase("localhost", 3333)
    inst.connect()
    return inst


def _assert_ack_sent(dut):
    dut._socket.send.assert_called_once_with(b"+")


def _assert_nack_sent(dut):
    dut._socket.send.assert_called_once_with(b"-")


def _assert_ctrl_c_sent(dut):
    dut._socket.send.assert_called_once_with(b"\x03")


def _assert_nothing_sent(dut):
    dut._socket.send.assert_not_called()


def test_connect_disconnect(dut_unconnected):
    dut_unconnected.connect()
    dut_unconnected._socket.connect.assert_called_with(("localhost", 3333))
    dut_unconnected._socket.connect.assert_called_once()

    with pytest.raises(RuntimeError) as e:
        dut_unconnected.connect()
    assert "Already connected" in str(e.value)
    dut_unconnected._socket.connect.assert_called_once()

    socket_backup = dut_unconnected._socket
    dut_unconnected.disconnect()
    assert dut_unconnected._socket is None
    socket_backup.shutdown.assert_called_once()
    socket_backup.close.assert_called_once()

    dut_unconnected.disconnect()
    assert dut_unconnected._socket is None
    # Second disconnect is a no-op


def test_send_packet_unconnected(dut_unconnected):
    with pytest.raises(RuntimeError) as e:
        dut_unconnected.send_packet(b"abc")
    assert "Can't send data, not connected" in str(e.value)


def test_recv_packet_unconnected(dut_unconnected):
    with pytest.raises(RuntimeError) as e:
        dut_unconnected.recv_packet()
    assert "Can't receive data, not connected" in str(e.value)


def test_send_packet(dut):
    with mock.patch.object(dut, "check_ack"):
        dut.send_packet(b"abc")
        dut._socket.send.assert_called_once_with(b"$abc#26")
        dut.check_ack.assert_called_once()


def test_send_packet_custom_checksum(dut):
    with mock.patch.object(dut, "check_ack"):
        dut.send_packet(b"abc", custom_checksum=b"12")
        dut._socket.send.assert_called_once_with(b"$abc#12")
        dut.check_ack.assert_called_once()


def test_send_packet_no_ack_mode(dut):
    with mock.patch.object(dut, "check_ack"):
        dut.set_no_ack_mode(True)
        dut.send_packet(b"abc")
        dut._socket.send.assert_called_once_with(b"$abc#26")
        dut.check_ack.assert_not_called()


def test_send_packet_explicit_no_ack(dut):
    with mock.patch.object(dut, "check_ack"):
        dut.send_packet(b"abc", check_ack=False)
        dut._socket.send.assert_called_once_with(b"$abc#26")
        dut.check_ack.assert_not_called()


def test_check_ack(dut):
    dut._socket.recv.return_value = b"+"
    dut.check_ack()

    dut._socket.recv.return_value = b"-"
    with pytest.raises(ProtocolError):
        dut.check_ack()

    dut._socket.recv.return_value = b"garbage"
    with pytest.raises(ProtocolError):
        dut.check_ack()


def test_send_ack(dut):
    dut.send_ack()
    _assert_ack_sent(dut)


def test_send_nack(dut):
    dut.send_nack()
    _assert_nack_sent(dut)


def test_send_ctrl_c(dut):
    dut.send_ctrl_c()
    _assert_ctrl_c_sent(dut)


def _check_recv_packet(dut, is_no_ack: bool):
    recv_data = [b"$ab", b"c#", b"2", b"6garbage", b"another_mess"]
    dut._socket.recv.side_effect = recv_data
    assert dut.recv_packet() == b"$abc#26"
    assert dut._socket.recv.call_count == 4
    assert dut._recv_buf == b"garbage"
    if is_no_ack:
        _assert_nothing_sent(dut)
    else:
        _assert_ack_sent(dut)


def test_recv_packet(dut):
    _check_recv_packet(dut, is_no_ack=False)


def test_recv_packet_no_ack_mode(dut):
    dut.set_no_ack_mode(True)
    _check_recv_packet(dut, is_no_ack=True)


def test_recv_packet_too_long(dut):
    recv_data = [b"$ab", b"c" * dut.MAX_RECV_PACKET]
    dut._socket.recv.side_effect = recv_data

    with pytest.raises(ProtocolError) as e:
        dut.recv_packet()
    assert "Excessive packet received" in str(e.value)


def test_recv_packet_no_timeout(dut):
    recv_data = [b"$a", b"bc", b"#26"]
    dut._socket.recv.side_effect = recv_data

    with mock.patch("time.time") as time_mock:
        time_mock.side_effect = [1000.0, 1001.0, 1002.0, 1003.0]
        dut.recv_packet() == b"$abc#26"


def test_recv_packet_timeout_reached(dut):
    recv_data = [b"$a", b"bc", b"#26"]
    dut._socket.recv.side_effect = recv_data

    with mock.patch("time.time") as time_mock:
        time_mock.side_effect = [1000.0, 1002.0, 1004.0, 1006.0]
        with pytest.raises(RecvTimeoutError):
            dut.recv_packet()


def test_recv_packet_garbage(dut):
    recv_data = [b"garbage$abc#26"]
    dut._socket.recv.side_effect = recv_data

    with pytest.raises(ProtocolError) as e:
        dut.recv_packet()
    assert "Unexpected character at the start of packet" in str(e.value)


def test_recv_and_decode_packet_data(dut):
    dut._socket.recv.side_effect = [b"$ab}C", b"d#", b"e7"]
    assert dut.recv_and_decode_packet_data() == b"abcd"
    _assert_ack_sent(dut)
