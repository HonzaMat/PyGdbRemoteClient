# SPDX-License-Identifier: MIT

from typing import Tuple, Union

from . import utils
from .client_base import GdbRemoteClientBase


class GdbRemoteClient:
    def __init__(self, host: str, port: int) -> None:
        self._client_base = GdbRemoteClientBase(host, port)

    def connect(self) -> None:
        self._client_base.connect()

    def disconnect(self) -> None:
        self._client_base.disconnect()

    def set_recv_timeout(self, timeout: float) -> None:
        self._client_base.set_recv_timeout(timeout)

    def set_no_ack_mode(self, no_ack_mode: bool) -> None:
        self._client_base.set_no_ack_mode(no_ack_mode)

    def _do_send_cmd(self, cmd_text: Union[str, bytes]) -> None:
        if isinstance(cmd_text, bytes):
            cmd_bytes = cmd_text
        elif isinstance(cmd_text, str):
            try:
                cmd_bytes = cmd_text.encode("ascii")
            except UnicodeDecodeError as e:
                raise ValueError(
                    "Provided string contains non-ascii characters. "
                    "Binary commands should be provided as 'bytes', not 'str'."
                ) from e
        else:
            raise TypeError("Expected command text to be an ASCII string or bytes")

        self._client_base.send_packet(cmd_bytes)

    def cmd(self, cmd_text: Union[str, bytes]) -> str:
        reply = self.cmd_bin_reply(cmd_text)
        try:
            return reply.decode("ascii")
        except UnicodeDecodeError:
            raise RuntimeError(
                "Expected ASCII-only response but received binary characters"
            )

    def cmd_bin_reply(self, cmd_text: Union[str, bytes]) -> bytes:
        # FIXME: There should be possibility of different timeouts
        # for ACK and for repsonse.

        # FIXME: The code below does not try to recover from the below (unlikely)
        # protocol errors. They are simply reported as exceptions. No retransmission
        # is attempted.
        # - Receive of NACK
        # - Receive of garbage bytes before packet

        self._do_send_cmd(cmd_text)
        reply = self._client_base.recv_and_decode_packet_data()
        return reply

    def cmd_no_reply(self, cmd_text: Union[str, bytes]) -> None:
        self._do_send_cmd(cmd_text)

    def ctrl_c(self) -> None:
        self._client_base.send_ctrl_c()

    def get_stop_reply(self) -> Tuple[str, str]:
        console_text = ""
        while True:
            reply = self._client_base.recv_and_decode_packet_data()
            reply_str = reply.decode("ascii")  # TODO: raise an error?
            if reply_str.startswith("O"):
                # Received console output ("O" message). Keep waiting
                # for the actual stop reply ("W", "T", etc.) that will
                # arrive later.
                console_text += utils.ascii_from_hex(reply_str[1:])
                continue
            else:
                # Stop reply was received.
                return reply_str, console_text
