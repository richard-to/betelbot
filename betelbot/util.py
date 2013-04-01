import fcntl
import os
import select
import signal
import sys 
import termios
import time
import tty


def signalHandler(signal, frame):
    # Callback to make sure scripts exit cleanly.
    #
    # Tornado servers don't stop cleanly when using Ctrl+C. I can't remember
    # why this behavior occurs.
    #
    # Callback is used as a param for this function
    # signal.signal(signal.SIGINT, signalHandler).
    sys.exit(0)


class NonBlockingTerm:

    def run(self, cb):
        signal.signal(signal.SIGINT, signalHandler)
        
        old_settings = termios.tcgetattr(sys.stdin)
        
        fd = sys.stdin.fileno()
        fl = fcntl.fcntl(fd, fcntl.F_GETFL)
        fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)

        try:
            tty.setcbreak(sys.stdin.fileno())
            while True:
                time.sleep(.3)
                if self.hasData():
                    cb()
        finally:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)

    def hasData(self):
        return select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], [])


def main():
    pass


if __name__ == '__main__':
    main()
