class DingApiException(Exception):
    def __init__(self, *args, **kwargs):
        self.msg = "".join(map(str, args))
        super(DingApiException, self).__init__(*args, **kwargs)

    def _message(self):
        return self.msg if self.msg else "Unknown Error"

    def __str__(self):
        message = self._message()
        return message

    def __unicode__(self):
        return self.__str__()


class MessageTypeException(DingApiException):
    def __str__(self):
        message = "|".join(["text", "image", "file", "oa", "voice", "link", "markdown", "action_card"])
        return "message_type key param must in %s" % message
