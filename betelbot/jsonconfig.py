import json


class JsonConfig(object):
    # Parses a json file and dynamically creates variables
    # for config values
    #
    # Currently defaults to a file in the module using a
    # relatively path. Not a good idea...
    #
    # Should probably not have a default and force user
    # to pass in as command line arg or better yet load from an
    # environment variable.
    #
    # The json file is only two levels deep.
    # The first level is a section and the second level contain
    # config values for the section.
    #
    # Config values can be any valid data. So you could have an object,
    # which could translate to a dict when loaded, etc.

    DEFAULT_FILEPATH = 'config/config.json'

    def __init__(self, filepath=None):
        filepath = filepath or Config.DEFAULT_FILEPATH
        jsonData = open(filepath).read()
        data = json.loads(jsonData)
        for section in data:
            sectionData = JsonConfigSection(data[section])
            setattr(self, section, sectionData)


class JsonConfigSection(object):
    # Parse data in a section and dynamically create
    # variable for instance.

    def __init__(self, data):
        for key in data:
            setattr(self, key, data[key])

    def dict(self):
        return self.__dict__


def main():
    pass

if __name__ == '__main__':
    main()