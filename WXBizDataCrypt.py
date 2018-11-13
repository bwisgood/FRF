import base64
import json
from Crypto.Cipher import AES

class WXBizDataCrypt:
    def __init__(self, appId, sessionKey):
        self.appId = appId
        self.sessionKey = sessionKey

    def decrypt(self, encryptedData, iv):
        # base64 decode
        sessionKey = base64.b64decode(self.sessionKey)
        encryptedData = base64.b64decode(encryptedData)
        iv = base64.b64decode(iv)

        cipher = AES.new(sessionKey, AES.MODE_CBC, iv)
        unpad = self._unpad(cipher.decrypt(encryptedData))
        # print(type(unpad))
        # print(unpad)
        a = unpad.decode('utf-8', 'ignore')
        # print(a)
        # print(type(a))
        decrypted = json.loads(a)
        # print(type(decrypted))
        # decrypted = json.loads(self._unpad(cipher.decrypt(encryptedData)))

        if decrypted['watermark']['appid'] != self.appId:
            raise Exception('Invalid Buffer')

        return decrypted

    def _unpad(self, s):
        return s[:-ord(s[len(s)-1:])]


if __name__ == '__main__':
    endata = "CKbxok3yan3UeILCJR0IgnrVnTnPkh9/+ATHYf6SWAXo6SIMek6HG2Pi2wDb0oR6oF0+JXB40W/AEdJVx96sHUrhbvQ6C4Bcj8yrYLIcV0sTDndFzRdxIs0nzmua62Jz8gGQQkgu9pO6WXUVi6xvtq0BHPU9H44jiUqN+X9+3PjagoMh15WN02AmIrLSjMUSUBTH2NTZwwh84VcgPNY5MA=="
    iv = "dEBUeoNi57XYgkTDEug+eQ=="
    session = "Sn7SzP2HobwFT6vCvQSJbQ=="
    pc = WXBizDataCrypt("wxff4006319f5577f1", session)
    c = pc.decrypt(endata, iv)

    print(c)