import abc
import fcntl
import inspect
import logging
import os
import os.path
import pkgutil
import select
import signal
import socket
import sys
import termios
import time
import tty

from datetime import datetime

from tornado.iostream import IOStream
from tornado.ioloop import IOLoop


def loadMsgDictFromPkg(pkgFile):
    # Dynamically loads all classes in specified package and
    # returns a dictionary with the key as the id value of the topic.
    #
    # This method should only be used in packages that contain only
    # topic and service typc classes.

    msgs = {}
    modules = loadPkgModules(pkgFile)
    for module in modules:
        msgs.update(loadMsgDict(loadModuleClasses(module)))
    return msgs


def loadMsgDict(msgObj):
    # Dynamically load topic classes into a
    # dictionary.
    #
    # Betelbot servers and clients use this dictionary to validate
    # topics.
    #
    # The key will be the id value of the topic class.

    msgDict = {}
    for name, obj in msgObj:
        msg = obj()
        msgDict[msg.id] = msg
    return msgDict


def loadPkgModules(pkgFile):
    # Dynamically loads all modules from a specified package.
    #
    # This function requires the directory path of the package.
    #
    # The main use case for this function is to load Topic definitions.
    # This means that the modules will be loaded from the Package
    # __init__.py file and will make it so the directory path can be retrieved
    # using the __file__ variable.

    pkgpath = os.path.dirname(pkgFile)
    modules = [loader.find_module(name).load_module(name)
        for loader, name, _ in pkgutil.iter_modules([pkgpath])]
    return modules


def loadModuleClasses(module):
    # Dynamically get all classes in a module.
    #
    # This function will only get classes defined a the specified module.
    # Classes that imported from within the module are ignored since that
    # would be the common use case.
    #
    # This returns a list of tuples with the format of (className, class)

    return inspect.getmembers(module, lambda o: inspect.isclass(o) and o.__module__ == module.__name__)


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

    def connect(self):
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

    # Log message templates
    LOG_MSG_SEND = 'Sending message'
    LOG_MSG_LISTEN = 'Listening for messages'
    LOG_CLIENT_QUIT = 'Client quit'
    LOG_INFO_GENERIC = '[%s, %s]%s'
    LOG_DATE_FORMAT = "%m-%d-%y %H:%M"

    # Message format for writing messages. Basically string followed by nullbyte.
    MSG_FORMAT = "{}{}"

    def __init__(self, stream, address, terminator='\0', **kwargs):
        # Inits a connection object with a connected stream

        self.stream = stream
        self.address = address
        self.terminator = terminator
        self.stream.set_close_callback(self.onClose)

        self.onInit(**kwargs)

    def onInit(self, **kwargs):
        return

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
        #
        # Currently not sure how to handle closed connections.
        #
        # One possibility is to call IOLoop.instance().stop(),
        # but this only works for non-threaded case.
        #
        # Additionally this appraoch uses the global object.
        #
        # Other drawbacks include non-persistent connections
        # where we don't necessarily want the loop closed.
        #
        # Maybe just catch the exception and exit gracefully in the
        # case of client connections?

        return

    def write(self, msg):
        # Sends msg to the server.

        self.logInfo(Connection.LOG_MSG_SEND)
        self.stream.write(Connection.MSG_FORMAT.format(msg, self.terminator), self.onWrite)

    def read(self):
        # Reads data from the stream until encounters the specified
        # terminator character.

        if not self.stream.reading():
            self.logInfo(Connection.LOG_MSG_LISTEN)
            self.stream.read_until(self.terminator, self.onRead)

    def close(self):
        # Disconnects client from server.
        if self.stream:
            self.logInfo(Connection.LOG_CLIENT_QUIT)
            self.stream.close()

    def logInfo(self, msg):
        dt = datetime.now().strftime(Connection.LOG_DATE_FORMAT)
        logging.info(Connection.LOG_INFO_GENERIC, self.address[0], dt, msg)


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

    def __init__(self, delay=0.3):
        # Delay is the amount of time to wait before checking if there is
        # key input data. This is to slowdown the infinite loop.

        self.delay = delay

    def run(self, cb):
        # This method starts the non-blocking terminal.
        #
        # A callback must be passed in to handle user key input. It will be called
        # for every key press.
        #
        # This implementation does not handle multi-byte characters, such as
        # arrow keys. A previous version of this code did handle this case, but
        # decided that it got kind of messy.

        signal.signal(signal.SIGINT, signalHandler)

        old_settings = termios.tcgetattr(sys.stdin)

        fd = sys.stdin.fileno()
        fl = fcntl.fcntl(fd, fcntl.F_GETFL)
        fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)

        try:
            tty.setcbreak(sys.stdin.fileno())
            while True:
                time.sleep(self.delay)
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
