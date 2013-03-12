class ValueTopic:
    def __init__(self, id, dataType):
        self.id = 'sense'
        self.dataType = ('red', 'green')

    def isValid(self, data):
        if len(data) == 1:
            return data[0] in self.dataType
        else:
            return False


class CmdTopic(ValueTopic):

    def __init__(self):
        super().__init__('cmd', ('h', 'j', 'k', 'l', 's'))


class MoveTopic(CmdTopic):
    def __init__(self):
        super().__init__()
        self.id = 'move'


class SenseTopic(ValueTopic):

    def __init__(self):
        super().__init__('sense', ('red', 'green'))


class HistogramTopic:

    def __init__(self):
        self.id = 'histogram'
        self.dataType = float

    def isValid(self, data):
        return True


cmdTopic = CmdTopic()
moveTopic = MoveTopic()
senseTopic = SenseTopic()
histogramTopic = HistogramTopic()

msgs = {
    CmdTopic.id: cmdTopic,
    MoveTopic.id: moveTopic,
    SenseTopic.id: senseTopic,
    HistogramTopic.id: histogramTopic
}