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