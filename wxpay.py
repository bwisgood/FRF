import requests
import random
import hashlib
import xmltodict

PAY_KEY = "yuanjia1234512345123451234512345"


class ReWxPayUtils(object):
    """
    1. 进行支付操作
        参数：
        appid:小程序id
        app_id :小程序id,
        timeStamp : 时间戳,
        package: 数据包,
        signType:签名类型
    """

    def __init__(self, appid, timeStamp, package, signType):
        self.appid = appid
        self.nonceStr = str(random.randint(0, 50000))
        # self.nonceStr   = "4973"
        self.timeStamp = timeStamp
        self.package = package
        self.signType = signType
        self.data = {
            'appId': self.appid,
            'nonceStr': self.nonceStr,
            'timeStamp': self.timeStamp,
            'package': self.package,
            'signType': self.signType
        }

    def sort_params(self):
        keys = list(self.data.keys())
        keys.sort()
        # print(keys)
        return self.gen_order_data(keys)

    def gen_order_data(self, keys):
        temp_data_list = [key + "=" + str(self.data.get(key)) for key in keys]
        temp_data_list.append("key=" + PAY_KEY)
        return "&".join(temp_data_list)

    def pre_data(self):
        """
        生成签名
        """
        s = self.sort_params()
        hl = hashlib.md5(s.encode())
        self.sign = hl.hexdigest().upper()
        return self.sign

    def check_sign(self):
        pass

    # def pre_data_xml(self):
    #     """
    #     生成参数
    #     :return: 返回xml data
    #     """
    #     s = self.sort_params()
    #     hl = hashlib.md5(s.encode())
    #     self.sign = hl.hexdigest().upper()
    #     self.data['paySign'] = self.sign
    #     _data = {"xml": self.data}
    #     req_data = xmltodict.unparse(_data, full_document=False)
    #     return req_data
        pass


class WxPayUtils(object):
    """
    1. 先进行预支付操作
        url:https://api.mch.weixin.qq.com/pay/unifiedorder
        参数：
        appid:小程序id
        mch_id:商户号
        nonce_str:随机数
        sign:签名
        body:商品描述（128）
        out_trade_no:
        total_fee:`订单总金额，单位为分`
        spbill_create_ip:终端ip
        notify_url:回调通知地址
        trade_type:JSAPI
        openid:openid
    """

    def __init__(self, app_id, mch_id, body,
                 out_trade_no, total_fee, spbill_create_ip,
                  openid):
        self.url = 'https://api.mch.weixin.qq.com/pay/unifiedorder'

        self.app_id = app_id
        self.mch_id = mch_id

        self.nonce_str = str(random.randint(0, 50000))

        self.body = body
        self.out_trade_no = out_trade_no
        self.total_fee = total_fee
        self.spbill_create_ip = spbill_create_ip
        self.notify_url = 'https://znsq.yuanjia101.com/mp/result'
        self.openid = openid
        self.trade_type = "JSAPI"
        self.data = {
            'appid': self.app_id,
            'mch_id': self.mch_id,
            'nonce_str': self.nonce_str,
            'body': self.body,
            'out_trade_no': self.out_trade_no,
            "total_fee": self.total_fee,
            'spbill_create_ip': self.spbill_create_ip,
            'notify_url': self.notify_url,
            'openid': self.openid,
            'trade_type': self.trade_type
        }

    def sort_params(self):
        keys = list(self.data.keys())
        keys.sort()
        return self.gen_order_data(keys)

    def gen_order_data(self, keys):
        temp_data_list = [key + "=" + str(self.data.get(key)) for key in keys]
        temp_data_list.append("key=" + PAY_KEY)
        return "&".join(temp_data_list)

    def pre_data(self):
        """
        生成参数
        :return: 返回xml data
        """
        s = self.sort_params()
        hl = hashlib.md5(s.encode())
        self.sign = hl.hexdigest().upper()
        self.data['sign'] = self.sign
        _data = {"xml": self.data}
        req_data = xmltodict.unparse(_data, full_document=False)
        print(req_data)
        return req_data

    def do_pre_order(self):
        data = self.pre_data()
        print(    data    )
        response = requests.post(url=self.url, data=data)
        # print(response.content.decode("utf-8"))
        return response.content.decode()


if __name__ == '__main__':
    wx = WxPayUtils("wxff4006319f5577f1", '1487735602',
                    'ok', '20180908123521', '123011', '39.106.101.198',
                     'o4XK94m_1U0_jMCbGgo-lMHAmgAU')
    wx.do_pre_order()
    # wx = ReWxPayUtils("wxff4006319f5577f1", "1539794500", "prepay_id=wx18004140837391cff00f50a43023360539", "MD5", )
    # print(wx.pre_data_xml())
