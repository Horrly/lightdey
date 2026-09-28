import uuid

import pytest
from rest_framework.test import APIClient

from power.models import Area


def device_client(device_id=None, ip="10.0.0.1"):
    client = APIClient(REMOTE_ADDR=ip)
    client.credentials(HTTP_X_DEVICE_ID=device_id or str(uuid.uuid4()))
    return client


@pytest.fixture
def api():
    return device_client()


@pytest.fixture
def make_client():
    return device_client


@pytest.fixture
def yaba(db):
    return Area.objects.create(name="Yaba", city="Lagos", state="Lagos")


@pytest.fixture
def report(api):
    def _report(area, state, client=None):
        return (client or api).post(f"/api/areas/{area.slug}/reports/", {"state": state}, format="json")

    return _report
