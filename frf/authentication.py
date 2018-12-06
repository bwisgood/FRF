"""
    1.先获取到permission_model和role_model
    2.查询当前用户的role 再去permission表中查询是否有对应的permission
    User:
        role_id

    Role:
        id
        name

    Permission:
        id
        method
        url
            "/url/url"

    RolePermissionMid:
        id
        role_id
        permission_id
"""

from flask import jsonify
from .response_code import RET


def singleton(cls):
    _instance = {}

    def _singleton(*args, **kwargs):
        if cls not in _instance:
            _instance[cls] = cls(*args, **kwargs)
        return _instance[cls]

    return _singleton


@singleton
class AuthManager(object):

    def __init__(self, permission_model, role_model, mid_model):
        self.permission_model = permission_model
        self.role_model = role_model
        self.mid_model = mid_model
        self.method_field = "method"
        self.url_field = "url"

    def check_permission(self, role_id, method, url, func=None):
        if func:
            def wrapper(*args, **kwargs):

                return_code = self._check(role_id, method, url)
                if return_code >= 400:
                    return jsonify(code=RET.ROLEERR, msg='权限错误', data="")

                result = func(*args, **kwargs)
                return result

            return wrapper

    def _check(self, role_id, method, url):
        filter_data = {
            self.method_field: method,
            self.url_field: url
        }
        permission = self.permission_model.query.filter(**filter_data).first()
        if not permission:
            return 404

        tokenizer = self.mid_model.query.filter(role_id=role_id, permission_id=permission.id).first()
        if not tokenizer:
            return 403
        return 200
