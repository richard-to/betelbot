import sys, os, re
import logging

from tornado.ioloop import IOLoop
from tornado.iostream import IOStream
from tornado.netutil import TCPServer

topics = {
    "betelbot_move": []
}

class BetelBotServer(TCPServer):
 
    def __init__(self, io_loop=None, ssl_options=None, **kwargs):
        logging.info('BetelBot Server is running.')
        TCPServer.__init__(self, io_loop=io_loop, ssl_options=ssl_options, **kwargs)
 
    def handle_stream(self, stream, address):
        BetelBotConnection(stream, address)


class BetelBotConnection(object):
 
    stream_set = set([])
    
    def __init__(self, stream, address):
        logging.info('Received a new connection from %s', address)
        self.stream = stream
        self.address = address
        self.stream_set.add(self.stream)
        self.stream.set_close_callback(self._on_close)
        self.stream.read_until('\n', self._on_read_line)
 
    def _on_read_line(self, data):
        logging.info('Reading a message from %s', self.address)
        tokens = data.strip().split(" ")
        if len(tokens) == 3 and tokens[0] == 'publish' and tokens[1] in topics:
            logging.info('Publishing a message from %s', self.address)
            subscribers = topics[tokens[1]]
            for subscriber in subscribers:
                subscriber.stream.write(data, subscriber._on_write_complete)
        elif len(tokens) == 2 and tokens[0] == 'subscribe' and tokens[1] in topics:
            logging.info('Subscribing to a topic from %s', self.address)
            topics[tokens[1]].append(self)
        
        if not self.stream.reading():
            self.stream.read_until('\n', self._on_read_line)

    def _on_write_complete(self):
        logging.info('Sending a message to %s', self.address)
        if not self.stream.reading():
            self.stream.read_until('\n', self._on_read_line)
 
    def _on_close(self):
        logging.info('Client quit %s', self.address)
        for topic in topics:
            logging.info("Unsubscribing client from %s topic from %s", topic, self.address)
            if self in topics[topic]:
                topics[topic].remove(self)
        self.stream_set.remove(self.stream)

if __name__ == '__main__':
    logger = logging.getLogger('')
    logger.setLevel(logging.INFO)

    server = BetelBotServer()
    server.listen(8888)
    IOLoop.instance().start()