#!/usr/bin/env python

import sys
import threading

from tornado.ioloop import IOLoop

import jsonrpc

from client import BetelbotClientConnection
from config import JsonConfig
from robosim import RobotMethod
from topic import getTopicFactory
from util import NonBlockingTerm, Client


def threadedLoop():
    # Need to run the Tornado IO loop in its own thread,
    # otherwise it will block terminal input.

    IOLoop.instance().start()


class TeleopKey(object):
    POWER = 'p'
    MANUAL = 'm'
    AUTONOMOUS = 'a'
    RESET = 'r'
    WAYPOINT = 'w'
    INFO = 'i'


class Teleop(object):

    MSG_SERVICES_READY =  "[Services registered. Teleop ready.]"
    MSG_SERVICES_LOADING = "[Registering services. Please wait.]"

    def __init__(self, conn, topics, location, waypoint):
        self.conn = conn
        self.topics = topics
        self.location = location
        self.waypoint = waypoint
        self.ready = False
        self.power = None

    def run(self):
        self.conn.subscribe(self.topics.power.id, lambda topic, data: self.onPowerResponse(data))
        self.conn.subscribe(self.topics.mode.id, self.onTopicPublished)
        self.conn.subscribe(self.topics.cmd.id, self.onTopicPublished)
        self.conn.batchLocate(self.onBatchLocateResponse,
            [RobotMethod.POWER, RobotMethod.MODE, RobotMethod.STATUS])

    def printInstructions(self):
        # Prints Betelbot control instructions to console

        cmdTopic = self.topics.cmd
        print 'Commands List'
        print '-----------------------'
        print '[{}] Gets information on robot status.'.format(TeleopKey.INFO)
        print '[{}] Toggles robot power on/off.'.format(TeleopKey.POWER)
        print '[{}] Switches to manual mode.'.format(TeleopKey.MANUAL)
        print '[{}] Switches to autonomous mode.'.format(TeleopKey.AUTONOMOUS)
        print '[{}] Resets robot to default location.'.format(TeleopKey.RESET)
        print '[{}] Sets default waypoint.'.format(TeleopKey.WAYPOINT)
        print '[{}, {}, {}, {}] Controls robot.'.format(
            cmdTopic.left, cmdTopic.down, cmdTopic.up, cmdTopic.right)
        print '[{}] Stops robot.'.format(cmdTopic.stop)

    def onPowerResponse(self, result):
        if self.topics.power.isValid(*result):
            self.onServiceResponse(RobotMethod.POWER, result)
            self.power = result[0]

    def onServiceResponse(self, method, result):
        if result:
            print '[{}]{}'.format(method, ' '.join(result))

    def onTopicPublished(self, topic, data=None):
        # Debugging callback to make test if commands are
        # being received and published.

        if data:
            print '[{}]{}'.format(topic, ' '.join(data))

    def onInput(self):
        # When terminal receives key input, this input is published
        # if it matches the accepted values of the command topic.

        if self.ready is not True:
            print Teleop.MSG_SERVICES_LOADING

        conn = self.conn
        topics = self.topics

        c = sys.stdin.read(1)
        if topics.cmd.isValid(c):
            conn.publish(topics.cmd.id, c)
        elif c == TeleopKey.POWER:
            power = topics.power.toggle(self.power)
            conn.robot_power(self.onPowerResponse, power)
        elif c == TeleopKey.MANUAL:
            conn.robot_mode(
                lambda result: self.onServiceResponse(RobotMethod.MODE, result),
                topics.mode.manual)
        elif c == TeleopKey.AUTONOMOUS:
            conn.robot_mode(
                lambda result: self.onServiceResponse(RobotMethod.MODE, result),
                topics.mode.autonomous)
        elif c == TeleopKey.RESET:
            conn.publish(topics.location.id, *self.location)
        elif c == TeleopKey.WAYPOINT:
            conn.publish(topics.waypoint.id, *self.waypoint)
        elif c == TeleopKey.INFO:
            conn.robot_status(
                lambda result: self.onServiceResponse(RobotMethod.STATUS, result))

    def onBatchLocateResponse(self, found):
        if found:
            self.conn.robot_status(self.onInitialRobotStatus)

    def onInitialRobotStatus(self, result):
        if self.topics.robot_status.isValid(*result):
            print Teleop.MSG_SERVICES_READY
            self.ready = True
            self.power = result[0]
            self.onServiceResponse(RobotMethod.STATUS, result)


def main():
    # Starts up a client connection to publish commands to Betelbot server.

    cfg = JsonConfig()
    topics = getTopicFactory()

    client = Client('', cfg.server.port, BetelbotClientConnection)
    conn = client.connect()

    thread = threading.Thread(target=threadedLoop)
    thread.daemon = True
    thread.start()

    teleop = Teleop(conn, topics, cfg.teleop.location, cfg.teleop.waypoint)
    teleop.printInstructions()
    teleop.run()

    term = NonBlockingTerm()
    term.run(teleop.onInput)


if __name__ == "__main__":
    main()