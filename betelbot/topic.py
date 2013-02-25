class MoveTopic:

    dataType = ('1', '2', '3', '4')

    @staticmethod
    def isValid(data):
        if len(data) == 1:
            return data[0] in MoveTopic.dataType
        else:
            return False


msgs = {
    'move': MoveTopic
}