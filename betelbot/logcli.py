import ConfigParser
import logging
import signal

from tornado.ioloop import IOLoop

from util import BetelBotClient, signalHandler
from topic import msgs


def onTopicPublished(topic, data=None):
    if data:
        print '[{}]{}'.format(topic, ' '.join(map(str, data)))


def main():
    signal.signal(signal.SIGINT, signalHandler)

    config = ConfigParser.SafeConfigParser()
    config.read('config/default.cfg')
    client = BetelBotClient('', config.getint('server', 'port'))
    for msg in msgs:
        client.subscribe(msg, onTopicPublished)
    IOLoop.instance().start()


if __name__ == "__main__":
    main()