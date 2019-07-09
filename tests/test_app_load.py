import pytest
from flask import current_app


def test_app(client):
    assert current_app.config.get("TESTING") is True
    assert current_app.extensions.get("frf") is not None

#
# def test_base_api(client):
#     resp = client.get("/persons")
#     assert resp.status_code == 200
#     # assert resp.json
#     resp_data = resp.json
#     assert resp_data is not None
#
#     inner_data = resp_data.get("data")
#     assert isinstance(inner_data, list) is True
#     assert len(inner_data) > 0


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


if __name__ == '__main__':
    pytest.main()
