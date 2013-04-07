from topic import ValueTopic

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
        super(CmdTopic, self).__init__('cmd', ('h', 'j', 'k', 'l', 's'), 1)


class MoveTopic(CmdTopic):
    # The MoveTopic differs from the CmdTopic in that this topic is 
    # published by the Robot after it completes its move.
    
    def __init__(self):
        super(MoveTopic, self).__init__()
        self.id = 'move'


class SenseTopic(object):
    # Placeholder PathTopic for now.
    # 
    # Best way to validate?

    def __init__(self):
        self.id = 'sense'

    def isValid(self, *data):
        return True


class PathTopic(object):
    # Placeholder PathTopic for now.
    # 
    # Best way to validate?

    def __init__(self):
        self.id = 'path'

    def isValid(self, *data):
        return True


class DirectionsTopic(object):
    # Placeholder DirectionsTopic for now.
    # 
    # Best way to validate?

    def __init__(self):
        self.id = 'directions'

    def isValid(self, *data):
        return True


class ParticleTopic(object):
    def __init__(self):
        self.id = 'particle'

    def isValid(self, *data):
        return True                