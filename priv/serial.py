import errno
import fcntl
import os
import select
import sys
import termios
import time
import tty


def write_all(fd, data):
    deadline = time.monotonic() + 1.5
    while data:
        if not select.select([], [fd], [], max(0, deadline - time.monotonic()))[1]:
            raise TimeoutError(errno.ETIMEDOUT, "serial write")
        try:
            data = data[os.write(fd, data):]
        except BlockingIOError:
            continue


def bridge(device):
    fd = os.open(device, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
    fcntl.ioctl(fd, termios.TIOCEXCL)
    try:
        tty.setraw(fd)
        attrs = termios.tcgetattr(fd)
        attrs[4:6] = [termios.B115200, termios.B115200]
        termios.tcsetattr(fd, termios.TCSANOW, attrs)
        termios.tcflush(fd, termios.TCIOFLUSH)
        os.write(1, b"R")
        while True:
            ready, _, _ = select.select([0, fd], [], [])
            for source in ready:
                data = os.read(source, 65536)
                if not data:
                    return
                write_all(fd if source == 0 else 1, data)
    finally:
        try:
            fcntl.ioctl(fd, termios.TIOCNXCL)
        finally:
            os.close(fd)


try:
    bridge(sys.argv[1])
except OSError as error:
    if error.errno not in (errno.ENOENT, errno.EBUSY, errno.ENODEV, errno.EIO, errno.EACCES, errno.ETIMEDOUT):
        raise
    sys.exit(1)
