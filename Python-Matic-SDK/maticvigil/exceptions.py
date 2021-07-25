class EVBaseException(Exception):
    def __init__(self, msg):
        super(EVBaseException, self).__init__(msg)
        self._msg = msg
        # Exception.__init__(self, msg)
    def __str__(self):
        return self._msg

class EVConnectionError(EVBaseException):
    def __init__(self, msg, exc_obj):
        super(EVConnectionError, self).__init__(msg)
        self.original_exc_obj = exc_obj
        self._msg = "\n%s\nOriginal exception:\n%s" %(msg, exc_obj)

    def __str__(self):
        return self._msg

class EVHTTPError(EVBaseException):
    def __init__(self, request_url, request_body, status_code, response_body):
        _msg = "\nRequest URL: %s\nRequest body: %s\nResponse HTTP status: %s\nResponse body: %s" % (request_url, request_body, status_code, response_body)
        super(EVHTTPError, self).__init__(_msg)
        self._request_url = request_url
        self._request_body = request_body
        self._status_code = status_code
        self._msg = _msg

    def __str__(self):
        return self._msg

class EVAPIError(EVHTTPError):
    def __init__(self, request_url, request_body, status_code, response_body):
        super(EVAPIError, self).__init__(request_url, request_body, status_code, response_body)

