import json


# Betelbot servers and clients communicate using JSON-RPC 2.0.
# 
# JSON-RPC 2.0 was chosen for its simpicity and compactness, compared to XML-RPC.
# Compatibility with web interfaces was another benefit of using this protocol.
#
# The JSON-RPC 2.0 spec can be found here: http://www.jsonrpc.org/specification.


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
        
        msg[JSONRPC] = self.VERSION
        return json.dumps(msg, cls=self.jsonEncoder)


def main():
    pass


if __name__ == '__main__':
    main()