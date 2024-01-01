# SPDX-License-Identifier: MIT


class GdbRemoteClientError(Exception):
    pass


class PacketFormatError(GdbRemoteClientError):
    pass


class ProtocolError(GdbRemoteClientError):
    pass


class RecvTimeoutError(GdbRemoteClientError):
    pass
