import ConfigParser
import logging
import os
import re
import signal
import sys
from datetime import datetime

from tornado.ioloop import IOLoop
from tornado.iostream import IOStream
from tornado.netutil import TCPServer

from topic import msgs
from util import signal_handler


topics = msgs
topicNames = dict((key,[]) for key in msgs.keys())

class BetelBotServer(TCPServer):
 
    def __init__(self, io_loop=None, ssl_options=None, **kwargs):
        logging.info('BetelBot Server is running')
        TCPServer.__init__(self, io_loop=io_loop, ssl_options=ssl_options, **kwargs)
 
    def handle_stream(self, stream, address):
        BetelBotConnection(stream, address)


class BetelBotConnection(object):
 
    streamSet = set([])

    def __init__(self, stream, address):
        self.stream = stream
        self.address = address
        self.streamSet.add(self.stream)
        self.stream.set_close_callback(self._onClose)
        self.stream.read_until('\n', self._onReadLine)
        self._logInfo('Received a new connection')
 
    def _onReadLine(self, data):
        self._logInfo('Reading a message')
        tokens = data.strip().split(" ")
        if len(tokens) > 2 and tokens[0] == 'publish' and tokens[1] in topicNames:
            topic = topics[tokens[1]]
            if topic.isValid(tokens[2:]):
                self._logInfo('Publishing a message')
                subscribers = topicNames[tokens[1]]
                for subscriber in subscribers:
                    subscriber.stream.write('{}\n'.format(' '.join(tokens[1:])), subscriber._onWriteComplete)
        elif len(tokens) == 2 and tokens[0] == 'subscribe' and tokens[1] in topicNames:
            self._logInfo('Subscribing to topic "{}"'.format(tokens[1]))
            topicNames[tokens[1]].append(self)
        
        if not self.stream.reading():
            self.stream.read_until('\n', self._onReadLine)

    def _onWriteComplete(self):
        self._logInfo('Sending message')
        if not self.stream.reading():
            self.stream.read_until('\n', self._onReadLine)
 
    def _onClose(self):
        self._logInfo('Client quit')
        for topic in topicNames:
            if self in topicNames[topic]:
                self._logInfo('Unsubscribing client from topic "{}"'.format(topic))        
                topicNames[topic].remove(self)
        self.streamSet.remove(self.stream)

    def _logInfo(self, msg):
        dt = datetime.now().strftime("%m-%d-%y %H:%M")
        logging.info('[%s, %s]%s', self.address[0], dt, msg)


def main():
    config = ConfigParser.SafeConfigParser()
    config.read('config/default.cfg')

    logger = logging.getLogger('')
    logger.setLevel(config.get('general', 'log_level'))

    signal.signal(signal.SIGINT, signal_handler)

    server = BetelBotServer()
    server.listen(config.getint('server', 'port'))
    IOLoop.instance().start()


if __name__ == '__main__':
    main()