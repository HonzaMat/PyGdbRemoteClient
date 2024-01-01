# SPDX-License-Identifier: MIT

import socket
import time
from typing import Optional

from . import utils
from .errors import ProtocolError, RecvTimeoutError


class GdbRemoteClientBase:
    # Larger timeout value is used for safety on slower target (e.g. simulations).
    DEFALUT_RECV_TIMEOUT: float = 5.0
    # Maximum number of bytes to receive from the socket in one go.
    RECV_BLOCK_SIZE: int = 1024
    # Maximum size of one received packet - safety limit.
    MAX_RECV_PACKET: int = 128 * 1024

    def __init__(self, host: str, port: int) -> None:
        if not (1 <= port <= 65535):
            raise ValueError(
                "Invalid TCP port number. Expected number in range 1 - 65535."
            )
        self._host = host
        self._port = port
        self._socket: Optional[socket.socket] = None
        self._recv_timeout = self.DEFALUT_RECV_TIMEOUT
        self._recv_time_start: float = 0.0
        self._recv_buf = b""
        self._no_ack_mode = False

    def set_recv_timeout(self, timeout: float) -> None:
        assert timeout > 0.0
        self._recv_timeout = timeout

    def set_no_ack_mode(self, no_ack_mode: bool) -> None:
        self._no_ack_mode = no_ack_mode

    def connect(self) -> None:
        if self._socket is not None:
            raise RuntimeError("Already connected")

        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.connect((self._host, self._port))
        self._socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self._recv_buf = b""

        # Each connection starts with ACKs enabled
        self._no_ack_mode = False

    def disconnect(self) -> None:
        if self._socket is not None:
            try:
                self._socket.shutdown(socket.SHUT_RDWR)
            except socket.error:
                pass
            try:
                self._socket.close()
            except socket.error:
                pass
        self._recv_buf = b""
        self._socket = None

    def send_packet(
        self,
        packet_data: bytes,
        custom_checksum: Optional[bytes] = None,
        check_ack: bool = True,
    ) -> None:
        data = utils.create_packet(packet_data, custom_checksum)
        self._send_bytes(data)
        if check_ack and not self._no_ack_mode:
            self.check_ack()

    def _send_bytes(self, data: bytes) -> None:
        assert len(data) > 0
        if self._socket is None:
            raise RuntimeError("Can't send data, not connected")
        self._socket.send(data)

    def _recv_bytes(self, requested: int) -> bytes:
        assert requested > 0

        if self._socket is None:
            raise RuntimeError("Can't receive data, not connected")

        while len(self._recv_buf) < requested:
            timeout_msg = (
                "Timeout elapsed. Did not manage to receive required data "
                "within {} sec".format(self._recv_timeout)
            )
            # Determine how much time is left to complete the receive operation
            time_left = self._get_recv_time_left()
            if time_left > 0:
                self._socket.settimeout(time_left)
                try:
                    self._recv_buf += self._socket.recv(self.RECV_BLOCK_SIZE)
                except socket.timeout as e:
                    # Timeout exhausted while blocked on recv()
                    raise RecvTimeoutError(timeout_msg) from e
            else:
                # Timeout exhausted before we even attempted the next recv()
                raise RecvTimeoutError(timeout_msg)

        result = self._recv_buf[0:requested]
        self._recv_buf = self._recv_buf[requested:]
        return result

    def _recv_byte(self) -> bytes:
        return self._recv_bytes(1)

    def _unrecv_bytes(self, b: bytes) -> None:
        self._recv_buf = b + self._recv_buf

    def _start_recv_timeout(self) -> None:
        self._recv_time_start = time.time()

    def _get_recv_time_left(self) -> float:
        assert self._recv_time_start > 0.0
        time_elapsed = time.time() - self._recv_time_start
        time_left = self._recv_timeout - time_elapsed
        if time_left < 0:
            return 0.0
        elif 0 < time_left < 1.0:
            # Safety: round up to 1 sec
            return 1.0
        else:
            assert time_left >= 1.0
            return time_left

    def check_ack(self) -> None:
        self._start_recv_timeout()
        c = self._recv_byte()
        is_ack = c == b"+"
        is_nack = c == b"-"

        if is_ack:
            # All OK
            return
        elif is_nack:
            raise ProtocolError("Received negative acknowledgement (NACK)")
        else:
            self._unrecv_bytes(c)
            raise ProtocolError(
                "Received unexpected character, neither ACK or NACK: " + repr(c)
            )

    def send_ack(self) -> None:
        self._send_bytes(b"+")

    def send_nack(self) -> None:
        self._send_bytes(b"-")

    def send_ctrl_c(self) -> None:
        self._send_bytes(b"\x03")

    def recv_packet(self, validate_and_ack: bool = True) -> bytes:
        self._start_recv_timeout()
        # FIXME: Partially-received packet is not put back to the received buffer
        # if a timeout occurs or too large packet is encountered.
        # For clean recovery from such errors, disconnect and reconnect must
        # be performed.

        packet = b""
        b = self._recv_byte()
        if b != b"$":
            raise ProtocolError(
                "Unexpected character at the start of packet. Expected '$', found "
                + repr(b)
            )
        packet += b
        while True:
            b = self._recv_byte()
            packet += b

            if len(packet) > self.MAX_RECV_PACKET:
                # Safety limit reached
                raise ProtocolError(
                    "Excessive packet received - larger than {} bytes".format(
                        self.MAX_RECV_PACKET
                    )
                )

            if b == b"#":
                # End of packet body
                break

        # Checksum
        packet += self._recv_bytes(2)

        if validate_and_ack:
            utils.validate_packet(packet)
            if not self._no_ack_mode:
                self.send_ack()

        return packet

    def recv_and_decode_packet_data(self) -> bytes:
        packet = self.recv_packet()
        _, packet_data, _, _ = utils.split_packet(packet)
        return utils.decode_packet_data(packet_data)
