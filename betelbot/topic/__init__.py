from util import loadMsgDictFromPkg


class ValueTopic(object):
    # Base topic that is used to validate parameters 
    # against a fixed set of values.
    #
    # This class should be considered abstract.
    # 
    # Topic classes should have constructors with that 
    # accept no parameters. This constraint makes it 
    # easier to dynamically load and instantiage classes.
    #
    # Additionally topics should be immutable since there 
    # can be multiple instances of the same Topic.
    
    def __init__(self, id, allowedValues, numParams=1):
        self.id = id
        self.allowedValues = allowedValues
        self.numParams = numParams

    def isValid(self, *data):
        if len(data) == self.numParams:
            return all(value in self.allowedValues for value in data)
        else:
            return False


def getTopics():
    # Loads all topic definitions into dictionary with topic id as key.

    return loadMsgDictFromPkg(__file__)