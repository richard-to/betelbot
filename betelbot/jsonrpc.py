import json


# Betelbot servers and clients communicate using JSON-RPC 2.0.
# 
# JSON-RPC 2.0 was chosen for its simpicity and compactness, compared to XML-RPC.
# Compatibility with web interfaces was another benefit of using this protocol.
#
# The JSON-RPC 2.0 spec can be found here: http://www.jsonrpc.org/specification.
#
# Currently only a JSON-RPC encoder class is implemented. For now, messages can be
# decoding using json.loads to turn json into python data types.


class JsonRpcProp:
    # JSON-RPC 2.0 message keywords/params.

    JSONRPC = 'jsonrpc'
    ID = 'id'
    METHOD = 'method'
    PARAMS = 'params'
    RESULT = 'result'
    ERROR = 'error'
    CODE = 'code'
    MESSAGE = 'message'


class JsonRpcError:
    # JSON-RPC 2.0 error codes and messages.
    #
    # Use codes -32000 to -32099 are for custom server errors.

    PARSE_ERROR = {JsonRpcProp.CODE: -32700, JsonRpcProp.MESSAGE: 'Parse error'}
    INVALID_REQUEST = {JsonRpcProp.CODE: -32600, JsonRpcProp.MESSAGE: 'Invalid Request'}
    METHOD_NOT_FOUND = {JsonRpcProp.CODE: -32601, JsonRpcProp.MESSAGE: 'Method not found'}
    INVALID_PARAMS = {JsonRpcProp.CODE: -326002, JsonRpcProp.MESSAGE: 'Invalid params'}
    INTERNAL_ERROR = {JsonRpcProp.CODE: -326003, JsonRpcProp.MESSAGE: 'Internal error'}


class JsonRpcEncoder:
    # Implements a barebones JSON-RPC 2.0 interface for sending messages.
    #
    # The encoder does not check the validity of params received. The params 
    # will be blindly encoded into JSON.
    # 
    # For instance, it is the responsibility of the user to not pass in None 
    # as a value for the id param.
    #
    # Batch requests are not currently supported.
    #
    # By default the encoder cannot encode complex objects correctly. The json
    # module only supports basic python types unless the JSONEncoder class is 
    # extended.

    VERSION = "2.0"

    def __init__(self, jsonEncoder=json.JSONEncoder):
        # Pass in a custom JSONEncoder if complex objects need to be encoded.

        self.jsonEncoder = jsonEncoder

    def request(self, id, method, *params):
        # Encodes a JSON object to be sent as a request.
        #
        # - An id and method name are required.
        # - Method params are optional.
        # - Method params can be in positional or named, ie. list or dict format.

        msg = {
            JsonRpcProp.ID: id,        
            JsonRpcProp.METHOD : method}
        if params:
            msg[JsonRpcProp.PARAMS] = params
        return self.encode(msg)

    def response(self, id, result):
        # Encodes a JSON object to be sent as a response to a request.
        #
        # - An id and result are required.

        return self.encode({
            JsonRpcProp.ID: id, 
            JsonRpcProp.RESULT: result})

    def error(self, id, error):
        # Encodes a JSON object to be sent as an error response to a request.
        #
        # - An id and error are required
        # - An error is an object with code and message params. 
        # - See JsonRpcError for default error codes.

        return self.encode({
            JsonRpcProp.ID: id,
            JsonRpcProp.ERROR: error})

    def notification(self, method, *params):
        # Encodes a JSON object to be sent as a notification.
        #
        # Notification do not need ids since they do not expect 
        # a response. If a response is needed, use a request.
        #
        # - Method name is required.
        # - Params are optional and can be positional or named.

        msg = {JsonRpcProp.METHOD : method}
        if params:
            msg[JsonRpcProp.PARAMS] = params
        return self.encode(msg)

    def encode(self, msg):
        # Helper that encodes dict into json and adds jsonrpc version param, 
        # which is required by JSON-RPC 2.0.
        #
        # This method should only be used privately since it does not check
        # that a valid message is provided.
        
        msg[JsonRpcProp.JSONRPC] = self.VERSION
        return json.dumps(msg, cls=self.jsonEncoder)


class JsonRpcIdIncrement:
    # Generate auto incrementing ids. Not the best option, 
    # but this will do for now.
    #
    # Ids are not guaranteed to be unique.
    # 
    # - If increment is set to 0 then the id will be the same each time.
    # - If multiple instances use the same parameters, then they will 
    #   generate the same sequence of ids.

    def __init__(self, start=1, prefix='', increment=1):
        # Defaults to generating the following sequence: 1, 2, 3,...
        # 
        # This can be changed by adding a prefix, changing the start 
        # number, and or changing the increment value.
        #
        # Assuming a prefix equal to "PREFIX" and a start of 1, then 
        # the first id will be PREFIX1".

        self.start = start
        self.prefix = prefix
        self.increment = increment

    def id(self):
        # Generates an id and then increments id.
        
        newId = ''.join([self.prefix, str(self.start)])
        self.start = self.start + self.increment
        return newId


def main():
    pass


if __name__ == '__main__':
    main()