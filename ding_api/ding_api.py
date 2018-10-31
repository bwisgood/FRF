import json
import pprint
import hashlib
import time

import requests

from extra_apps.ding_api.exc import DingApiException, MessageTypeException


class DingApi(object):
    def __init__(self, ding_corp_id, ding_corp_secret, ding_agent_id):
        self.ding_corp_id = ding_corp_id
        self.ding_corp_secret = ding_corp_secret
        self.ding_agent_id = ding_agent_id
        self.user_list = []
        self.simple_user_list = []

    def get_ding_access_token(self):
        """
        获取access_token
        :return:
        """
        from apps import redis_cli
        access_token = redis_cli.get("ding_access_token")
        if access_token is not None:
            return access_token

        req_url = "https://oapi.dingtalk.com/gettoken?corpid={}&corpsecret={}".format(self.ding_corp_id,
                                                                                      self.ding_corp_secret)
        # req_url = "https://oapi.dingtalk.com/gettoken?corpid=ding5a306c83d415da11&corpsecret
        # =psqRy5dB8_1v0zaP2gvNe_SRH8nkWc5fGxunryN-pyNXo2WLHsF42zmMpJDBLRDw"

        response = requests.get(req_url)
        response_dict = json.loads(response.text)
        # todo 获取errormsg
        access_token = response_dict.get("access_token")
        redis_cli.setex("ding_access_token", 7100, access_token)
        return access_token

    def get_ding_department(self):
        """
        获取钉钉所有部门
        :return:
        """
        access_token = self.get_ding_access_token()
        url = "https://oapi.dingtalk.com/department/list?access_token={}".format(access_token)
        response = requests.get(url)
        response_dict = response.json()
        departs_list = response_dict.get("department")
        pprint.pprint(departs_list)
        return departs_list

    def get_ding_user_list(self, department_id, offset=0, size=100):
        """
        获取某个部门用户列表（详细信息）
        :param department_id: 部门id
        :param offset: 偏移量 （第几页）
        :param size: 每页展示大小
        :return:
        """
        access_token = self.get_ding_access_token()
        url = "https://oapi.dingtalk.com/user/list?access_token={}&department_id={}&offset={}&size={}".format(
            access_token,
            department_id, offset, size)
        response = requests.get(url)
        response_dict = response.json()
        user_list = response_dict.get("userlist")
        self.user_list.extend(user_list)
        has_more = response_dict.get("hasMore")
        if bool(has_more):
            self.get_ding_user_list(department_id=department_id, offset=offset + size)

        return user_list

    def get_simple_ding_user_list(self, department_id, offset=0, size=20):
        """
        获取简单用户列表（简单信息）
        :param department_id: 部门id
        :param offset: 偏移量 （第几页）
        :param size: 每页展示大小
        :return:
        """
        access_token = self.get_ding_access_token()
        url = "https://oapi.dingtalk.com/user/simplelist?access_token={}&department_id={}&offset={}&size={}".format(
            access_token,
            department_id, offset, size)
        response = requests.get(url)
        response_dict = response.json()
        user_list = response_dict.get("userlist")
        self.simple_user_list.extend(user_list)
        has_more = response_dict.get("hasMore")
        if bool(has_more):
            self.get_ding_user_list(department_id=department_id, offset=offset + size)

        return user_list

    def get_all_user(self, simple=True):
        """
        获取所有用户
        :param simple: 是否展示简单用户信息，默认True
        :return:
        """
        departs = self.get_ding_department()
        departs_id_list = [depart.get("id") for depart in departs]
        all_user_list = []
        for depart_id in departs_id_list:
            if simple:
                all_user_list.extend(self.get_simple_ding_user_list(depart_id))
            else:
                all_user_list.extend(self.get_ding_user_list(depart_id))
        return all_user_list

    def get_user_info(self, user_id):
        """
        获取某个用户的详细信息
        :param user_id: user_id
        :return:
        """
        access_token = self.get_ding_access_token()
        url = "https://oapi.dingtalk.com/user/get?access_token={}&userid={}".format(access_token, user_id)
        response = requests.get(url)
        user_info = response.json()
        return user_info

    def get_admin_list(self):
        access_token = self.get_ding_access_token()
        url = "https://oapi.dingtalk.com/user/get_admin?access_token={}".format(access_token)
        response = requests.get(url)
        response_dict = response.json()
        admin_list = response_dict.get("admin_list")
        admin_id_list = [i.get("userid") for i in admin_list]
        all_admin_list = []
        for admin_id in admin_id_list:
            all_admin_list.append(self.get_user_info(admin_id))

        return all_admin_list

    def send_message(self, *args, **kwargs):

        msg_type_list = ["text", "image", "file", "oa", "voice", "link", "markdown", "action_card"]

        access_token = self.get_ding_access_token()
        url = 'https://oapi.dingtalk.com/message/send?access_token=' + access_token

        # 校验userid
        if len(args) > 1:
            user_id = "|".join(map(str, args))
        elif len(args) == 1:
            if isinstance(args[0], list):
                user_id = "|".join(map(str, args[0]))
            else:
                user_id = args[0]
        else:
            raise DingApiException(
                "param [user_id] can not be None"
            )
        # 校验msg_type
        if not kwargs:
            raise DingApiException(
                "[msgtype] and msg(text,image,file...etc) can not be none, "
                "Reference https://open-doc.dingtalk.com/docs/doc.htm?"
                "spm=a219a.7629140.0.0.4d4f4a97ZMdTl3&treeId=374&articleId=104972&docType=1")

        msg_type = kwargs.pop("msgtype", None)
        if not msg_type:
            raise DingApiException(
                "param [msgtype] can not be none"
            )

        if len(kwargs) > 1:
            raise DingApiException(
                "maybe you send more params"
            )
        elif len(kwargs) == 0:
            raise DingApiException(
                "param [msg(text,image,file,oa...etc)] cannot be null"
            )

        if list(kwargs.keys())[0] not in msg_type_list:
            raise MessageTypeException
        # 合并参数
        data = {
            "touser": user_id,
            "agentid": self.ding_agent_id,
            "msgtype": msg_type
        }
        data.update(kwargs)

        pprint.pprint(data)
        resp = requests.post(url=url, data=json.dumps(data))
        return resp.json()

    def get_js_ticket(self):
        access_token = self.get_ding_access_token()
        js_ticket_url = "https://oapi.dingtalk.com/get_jsapi_ticket?access_token={}".format(access_token)
        response = requests.get(js_ticket_url)
        ticket = response.json().get("ticket")
        return ticket

    def get_js_sign(self, url):
        ticket = self.get_js_ticket()
        nonce = os.urandom(10).hex()
        time_stamp = int(time.time())
        encrypt_str = "jsapi_ticket=" + ticket + "&noncestr=" + nonce + "&timestamp=" + str(time_stamp) + "&url=" + url

        hl = hashlib.sha1()
        hl.update(encrypt_str)
        sign = hl.hexdigest()

        return {"signature": sign, "agentid": self.ding_agent_id, "timeStamp": time_stamp, "nonceStr": nonce,
                "corpId": self.ding_corp_id}

    def check_code(self, code):
        access_token = self.get_ding_access_token()
        url = "https://oapi.dingtalk.com/user/getuserinfo?access_token={}&code={}".format(access_token, code)
        response = requests.get(url)
        response_dict = response.json()
        return response_dict
