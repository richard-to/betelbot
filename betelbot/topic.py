class CmdTopic:
    id = 'cmd'
    dataType = ('h', 'j', 'k', 'l', 's')
    
    @staticmethod
    def isValid(data):
        if len(data) == 1:
            return data[0] in CmdTopic.dataType
        else:
            return False


class MoveTopic:
    id = 'move'
    dataType = ('h', 'j', 'k', 'l', 's')

    @staticmethod
    def isValid(data):
        if len(data) == 1:
            return data[0] in MoveTopic.dataType
        else:
            return False


class SenseTopic:
    id = 'sense'
    dataType = ('red', 'green')

    @staticmethod
    def isValid(data):
        if len(data) == 1:
            return data[0] in SenseTopic.dataType
        else:
            return False


class HistogramTopic:
    id = 'histogram'
    dataType = float

    @staticmethod
    def isValid(data):
        return True


msgs = {
    CmdTopic.id: CmdTopic,
    MoveTopic.id: MoveTopic,
    SenseTopic.id: SenseTopic,
    HistogramTopic.id: HistogramTopic
}