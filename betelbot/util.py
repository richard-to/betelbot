import abc
import fcntl
import os
import select
import signal
import socket
import sys 
import termios
import time
import tty

from tornado.iostream import IOStream

def signalHandler(signal, frame):
    # Callback to make sure scripts exit cleanly.
    #
    # Tornado servers don't stop cleanly when using Ctrl+C. I can't remember
    # why this behavior occurs.
    #
    # Callback is used as a param for this function
    # signal.signal(signal.SIGINT, signalHandler).
    sys.exit(0)


class Client(object):
    # Client is a factory class to create client connections to a server
    #
    # - kwargs here is used to pass parameters to Connection objects

    def __init__(self, host, port, connection, terminator='\0', **kwargs):
        self.host = host
        self.port = port
        self.connection = connection
        self.terminator = terminator
        self.kwargs = kwargs

    def create(self):
        # Creates and returns a connection object for use.

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        stream = IOStream(sock)
        stream.connect((self.host, self.port))
        return self.connection(stream, sock.getsockname(), self.terminator, **self.kwargs)


class Connection(object):
    # Abstract connection class handles read, write, and close operations 
    # on a connected socket. The onRead method needs to be implemented.
    #
    # Connection objects can be use for both server and client connections.

    __metaclass__ = abc.ABCMeta

    def __init__(self, stream, address, terminator):
        # Inits a connection object with a connected stream

        self.stream = stream
        self.address = address
        self.terminator = terminator
        self.stream.set_close_callback(self.onClose)

    @abc.abstractmethod
    def onRead(self, data):
        # Invoked when streams reads to a terminator character.
        # Implement this callback to handle incoming data.
        return

    def onWrite(self):
        # Invoked when stream has finished writing. By default
        # the stream will listen for a response.

        self.read()

    def onClose(self):
        # Invoked when stream is closed.
        return

    def write(self, msg):
        # Sends msg to the server.

        self.stream.write("{}{}".format(msg, self.terminator), self.onWrite)

    def read(self):
        # Reads data from the stream until encounters the specified 
        # terminator character.

        if not self.stream.reading():
            self.stream.read_until(self.terminator, self.onRead)

    def close(self):
        # Disconnects client from server.

        self.stream.close()  



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
