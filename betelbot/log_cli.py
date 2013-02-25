import ConfigParser
import logging

from tornado.ioloop import IOLoop

from util import PubSubClient, signal_handler
from topic import msgs


def callback(data=None):
    if data:
        print data.strip()


def main():
    signal.signal(signal.SIGINT, signal_handler)

    config = ConfigParser.SafeConfigParser()
    config.read('config/default.cfg')
    client = PubSubClient('', config.getint('server', 'port'))
    for msg in msgs:
        client.subscribe(msg, callback)
    IOLoop.instance().start()


if __name__ == "__main__":
    main()