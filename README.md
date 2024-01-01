# Simple GDB Remote client library for Python

![Code Quality Workflow](https://github.com/HonzaMat/PyGdbRemoteClient/actions/workflows/code_quality.yml/badge.svg)
&nbsp; ![Unit Tests Workflow](https://github.com/HonzaMat/PyGdbRemoteClient/actions/workflows/unit_tests.yml/badge.svg)

## What is GDB Remote Protocol?

*GDB Remote Protocol* (also called *Remote Serial Protocol*, RSP) is a protocol used by [GDB](https://www.sourceware.org/gdb/) (or similar debuggers) for so called *remote debugging* &mdash; for debugging of processes running on a **different** system than where GDB itself runs.

Using the GDB Remote Protocol, GDB talks to so called *stub* &mdash; a small program on the target system, an agent that controls the debugged process.

Remote debugging (and thus GDB Remote Protocol) come to play in cases when the target system cannot run the whole GDB the usual way &mdash; e.g. for embedded systems.


## What is PyGdbRemoteClient?

`PyGdbRemoteClient` is a Python library that allows programs to talk to the remote stubs (as though they were GDB). 

The library was developed for for testing of [OpenOCD](https://www.openocd.org/), which is also a stub from the GDB point of view. However, it may be useful also in other cases when a Python program needs to communicate with a GDB stub.


## Quick start

```py
from gdb_remote_client import GdbRemoteClient

# Connect to stub running on localhost, TCP port 3333
cli = GdbRemoteClient("localhost", 3333) 
cli.connect()

# Example how to interact with the stub:

# cli.cmd("...") sends a command and returns the response
resp = cli.cmd("qSupported")
print("The remote stub supports these features: " + resp)  

resp = cli.cmd("g")
print("Values of general-purpose registers: " + resp)

resp = cli.cmd("vMustReplyEmpty")
if resp != "":
    raise RuntimeError("Unexpected reply to command vMustReplyEmpty")

# No-ack mode can be configured by cli.set_no_ack_mode(True)
resp = cli.cmd("QStartNoAckMode")
if resp != "OK":
    raise RuntimeError("The stub refused to enter the no-ack mode")
cli.set_no_ack_mode(True)  # no ACKs from now on

# Some commands don't produce the response immediately but only after
# the target halts (e.g. the vCont command). For such commands, 
# the cli.cmd_no_reply() method must be used.
cli.cmd_no_reply("vCont;c")  
time.sleep(2.0)
cli.ctrl_c()  # Interrupt the running process

# When the target halts, the stop reply from the stub can be fetched 
# by cli.get_stop_reply(). This method returns both the stop reply
# and the text, printed to the console during the program run.
stop_reply, console_text = cli.get_stop_reply()
print("Process halted with this stop reply: " + stop_reply)
if len(console_text) > 0:
    print("This console output was produced while the program ran: " + console_text)
else:
    print("No console output was produced while the program ran.")

# ...
# ...

# Finally, disconnect
cli.disconnect()

```


## Further documentation

(Under construction)


## References

GDB Remote Protocol description in GDB manual: https://sourceware.org/gdb/current/onlinedocs/gdb.html/Remote-Protocol.html

Remote debugging in GDB manual: https://sourceware.org/gdb/current/onlinedocs/gdb.html/Remote-Debugging.html#Remote-Debugging

Using OpenOCD as a stub for GDB: https://openocd.org/doc-release/html/GDB-and-OpenOCD.html#GDB-and-OpenOCD
