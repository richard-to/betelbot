import json


class JsonConfig(object):

    DEFAULT_FILEPATH = 'config/config.json'

    def __init__(self, filepath=None):
        filepath = filepath or Config.DEFAULT_FILEPATH
        jsonData = open(filepath).read()
        data = json.loads(jsonData)
        for section in data:
            sectionData = JsonConfigSection(data[section])
            setattr(self, section, sectionData)


class JsonConfigSection(object):

    def __init__(self, data):
        for key in data:
            setattr(self, key, data[key])

    def dict(self):
        return self.__dict__


def main():
    pass

if __name__ == '__main__':
    main()