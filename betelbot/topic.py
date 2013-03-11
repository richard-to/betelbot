class MoveTopic:

    dataType = ('1', '2', '3', '4', '5')

    @staticmethod
    def isValid(data):
        if len(data) == 1:
            return data[0] in MoveTopic.dataType
        else:
            return False


class SenseTopic:

    dataType = ('red', 'green')

    @staticmethod
    def isValid(data):
        if len(data) == 1:
            return data[0] in SenseTopic.dataType
        else:
            return False


class HistogramTopic:

    dataType = float

    @staticmethod
    def isValid(data):
        return True


msgs = {
    'move': MoveTopic,
    'sense': SenseTopic,
    'histogram': HistogramTopic
}