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
    # Makes it so terminal handles key input asynchronously.
    # 
    # The benefit is that we don't have to depend on readline, 
    # which will block until input is recieved. This prevents 
    # the terminal from receiving and outputting messages that may 
    # be sent by Betelbot server.
    #
    # This implementation only works in Linux and Mac since it uses OS specific 
    # functions. This has only been tested on a Mac.

    def run(self, cb):
        # This method starts the non-blocking terminal.
        # 
        # A callback must be passed in to handle user key input. It will be called 
        # for every key press.
        #
        # This implementation does not handle multi-byte characters, such as 
        # arrow keys. A previous version of this code did handle this case.

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
        # This method checks if we have any input from user.

        return select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], [])


def main():
    pass


if __name__ == '__main__':
    main()
