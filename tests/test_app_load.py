import pytest
from flask import current_app
from tests.common_app import Person

"""
path='/', base_url=None, query_string=None,
method='GET', input_stream=None, content_type=None,
content_length=None, errors_stream=None, multithread=False,
multiprocess=False, run_once=False, headers=None, data=None,
environ_base=None, environ_overrides=None, charset='utf-8',
mimetype=None
"""


def test_app(client):
    assert current_app.config.get("TESTING") is True
    assert current_app.extensions.get("frf") is not None


def test_base_api(client):
    resp = client.get("/persons")
    assert resp.status_code == 200
    # assert resp.json
    resp_data = resp.json
    assert resp_data is not None

    inner_data = resp_data.get("data")
    assert isinstance(inner_data, list) is True
    assert len(inner_data) > 0


def test_story(client):
    # 创建一个人
    post_data = {
        "name": "bw",
        "gender": "male"
    }

    resp = client.post("/persons", json=post_data, headers={"Content-Type": "application/json"})
    assert resp.status_code == 200
    assert resp.json.get("data").get("name") == "bw"
    assert resp.json.get("data").get("gender") == "male"
    person_id = resp.json.get("data").get("id")

    # 查看是否创建成功
    resp = client.get("/persons", query_string={"id": person_id})
    assert resp.status_code == 200
    assert resp.json.get("data") == {"id": person_id, "name": "bw", "gender": "male"}

    # 修改性别


def test_read_only(client):
    # 查询人员数据列表
    resp = client.get("/persons")
    assert resp.status_code == 200
    result_data = resp.json.get("data")
    assert result_data is not None

    person = result_data[0]

    # 查询单人的数据列表
    resp = client.get("/persons", query_string={"id": person.get("id")})
    resp_data = resp.json.get("data")
    assert person.get("id") == resp_data.get("id")
    assert person.get("name") == resp_data.get("name")
    assert person.get("gender") == resp_data.get("gender")

    # 修改单人的数据
    resp = client.put("/persons")


if __name__ == '__main__':
    pytest.main()
