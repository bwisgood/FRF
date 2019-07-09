import os
import sys

base = os.path.dirname(os.path.dirname(__file__))
sys.path.append(base)

import pytest
from tests.common_app import app as App


@pytest.fixture
def app():
    # app = App

    return App
