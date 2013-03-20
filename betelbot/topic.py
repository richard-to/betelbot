class ValueTopic(object):
    def __init__(self, id, dataType):
        self.id = id
        self.dataType = dataType

    def isValid(self, data):
        if len(data) == 1:
            return data[0] in self.dataType
        else:
            return False


class CmdTopic(ValueTopic):

    def __init__(self):
        super(CmdTopic, self).__init__('cmd', ('h', 'j', 'k', 'l', 's'))


class MoveTopic(CmdTopic):
    def __init__(self):
        super(MoveTopic, self).__init__()
        self.id = 'move'


class SenseTopic(ValueTopic):

    def __init__(self):
        super(SenseTopic, self).__init__('sense', ('red', 'green'))


class HistogramTopic:

    def __init__(self):
        self.id = 'histogram'
        self.dataType = float

    def isValid(self, data):
        return True


class SearchTopic:

    def __init__(self):
        self.id = 'search'
        self.dataType = float

    def isValid(self, data):
        return True


cmdTopic = CmdTopic()
moveTopic = MoveTopic()
senseTopic = SenseTopic()
histogramTopic = HistogramTopic()
searchTopic = SearchTopic()

msgs = {
    cmdTopic.id: cmdTopic,
    moveTopic.id: moveTopic,
    senseTopic.id: senseTopic,
    histogramTopic.id: histogramTopic,
    searchTopic.id: searchTopic
}