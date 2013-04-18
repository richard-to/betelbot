from topic import ValueTopic


class WaypointTopic(object):

    def __init__(self):
        self.id = 'waypoint'
        self.numParams = 2
        self.locationTopic = LocationTopic()

    def isValid(self, *data):
        return (len(data) == self.numParams and
            all(self.locationTopic.isValid(coord) for coord in data))


class LocationTopic(object):

    def __init__(self):
        self.id = 'location'
        self.numParams = 2

    def isValid(self, *data):
        return len(data) == self.numParams and all(isinstance(xy, int) for xy in data)


class RobotStatusTopic(object):

    def __init__(self):
        self.id = 'robot_status'
        self.numParams = 2
        self.powerTopic = PowerTopic()
        self.modeTopic = ModeTopic()

    def isValid(self, *data):
        return (len(data) == self.numParams and
            self.powerTopic.isValid(data[0]) and self.modeTopic.isValid(data[1]))


class PowerTopic(ValueTopic):

    def __init__(self):
        self.on = "on"
        self.off = "off"
        self.keys = (self.on, self.off)

        super(PowerTopic, self).__init__('power', self.keys, 1)

    def toggle(self, value):
        return self.on if value == self.off else self.off


class ModeTopic(ValueTopic):

    def __init__(self):
        self.autonomous = "autonomous"
        self.manual = "manual"
        self.keys = (self.autonomous, self.manual)

        super(ModeTopic, self).__init__('mode', self.keys, 1)


class CmdTopic(ValueTopic):
    # Command msgs contain directions for Betelbot to move. These messages
    # are usually published by a controller interface.
    #
    # Valid movements are left, down, up, right, and stop.
    #
    # Vi controls are used to avoid multibyte arrow keys.
    #
    # CommandTopic is slightly different than the MoveTopic.

    def __init__(self):

        self.left = 'h'
        self.down = 'j'
        self.up = 'k'
        self.right = 'l'
        self.stop = 's'
        self.keys = (self.left, self.down, self.up, self.right, self.stop)

        super(CmdTopic, self).__init__('cmd', self.keys, 1)


class MoveTopic(CmdTopic):
    # The MoveTopic differs from the CmdTopic in that this topic is
    # published by the Robot after it completes its move.

    def __init__(self):
        super(MoveTopic, self).__init__()
        self.id = 'move'


class SenseTopic(object):
    def __init__(self):
        self.id = 'sense'

    def isValid(self, *data):
        return True


class PathTopic(object):
    def __init__(self):
        self.id = 'path'

    def isValid(self, *data):
        return True


class DirectionsTopic(object):
    def __init__(self):
        self.id = 'directions'

    def isValid(self, *data):
        return True


class ParticleTopic(object):
    def __init__(self):
        self.id = 'particle'

    def isValid(self, *data):
        return True