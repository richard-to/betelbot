import ConfigParser
import logging
import signal

from tornado.ioloop import IOLoop

from util import PubSubClient, signal_handler
from topic import msgs


def onTopicPublished(topic, data=None):
    if data:
        print '[{}]{}'.format(topic, ' '.join(data))


def main():
    signal.signal(signal.SIGINT, signal_handler)

    config = ConfigParser.SafeConfigParser()
    config.read('config/default.cfg')
    client = PubSubClient('', config.getint('server', 'port'))
    for msg in msgs:
        client.subscribe(msg, onTopicPublished)
    IOLoop.instance().start()


if __name__ == "__main__":
    main()