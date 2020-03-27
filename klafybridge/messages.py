class Message:
    class Type:
        USER_MESSAGE = 0
        REQUEST = 1
        RESPONSE = 2
        USER_ACTION = 3

    class ContentType:
        TEXT = 0
        MEDIA = 1

    class RequestType:
        USER_LIST = 0

    def __init__(self, msgtype, **kwargs):
        self.kwargs = kwargs
        self.msgtype = msgtype

    def __getattr__(self, attr):
        try:
            return self.kwargs[attr]
        except:
            super().__getattr__(self, attr)

    def __repr__(self):
        if self.msgtype == self.Type.USER_MESSAGE:
            t = "USER_MESSAGE"
        elif self.msgtype == self.Type.REQUEST:
            t = "REQUEST"
        else:
            t = "RESPONSE"
        return "<Message of type %s, kwargs=%r>" % (t, self.kwargs)
