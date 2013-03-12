#!/usr/bin/env python

import ConfigParser
import logging
import random
import signal

from tornado.ioloop import IOLoop

from map import simple_world
from topic import HistogramTopic, MoveTopic, SenseTopic
from util import PubSubClient, signal_handler


class HistogramFilter:

    def __init__(self, client):
        self.client = client
        uniformP = 1.0 / len(simple_world)
        self.p = [uniformP] * len(simple_world)
        self.world = simple_world
        self.pHit = 0.6
        self.pMiss = 0.2
        self.pExact = 0.8
        self.pOvershoot = 0.1
        self.pUndershoot = 0.1
        self.client.subscribe(MoveTopic.id, self.onMovePublished)
        self.client.subscribe(SenseTopic.id, self.onSensePublished)

    def onSensePublished(self, topic, data=None):
        self.p = self.sense(self.p, data[0])
        print self.p
        self.client.publish(HistogramTopic.id, *self.p)

    def onMovePublished(self, topic, data=None):
        self.p = self.move(self.p, 1)
        print self.p
        self.client.publish(HistogramTopic.id, *self.p)

    def sense(self, p, Z):
        q=[]
        for i in range(len(p)):
            hit = (Z == self.world[i])
            q.append(p[i] * (hit * self.pHit + (1 - hit) * self.pMiss))
        s = sum(q)
        for i in range(len(q)):
            q[i] = q[i] / s
        return q

    def move(self, p, U):
        q = []
        for i in range(len(p)):
            s = self.pExact * p[(i - U) % len(p)]
            s = s + self.pOvershoot * p[(i - U - 1) % len(p)]
            s = s + self.pUndershoot * p[(i - U + 1) % len(p)]
            q.append(s)
        return q


def main():
    signal.signal(signal.SIGINT, signal_handler)

    config = ConfigParser.SafeConfigParser()
    config.read('config/default.cfg')

    client = PubSubClient('', config.getint('server', 'port'))
    hFilter = HistogramFilter(client)

    IOLoop.instance().start()

if __name__ == '__main__':
    main()
