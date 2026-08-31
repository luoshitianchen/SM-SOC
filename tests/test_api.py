"""SM SOC 领域测试：告警接入、研判、剧本、事件与统计。"""

import pytest
from fastapi.testclient import TestClient

from app import base
from app.main import VERSION, app


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setattr(base, "internal_api_key", lambda: "TEST")
    base.reset_state()
    from app.main import _init as init_db
    init_db()
    with TestClient(app) as c:
        c.headers["X-Internal-Token"] = "TEST"
        yield c


def _alert(client, severity="high", title="异常登录"):
    return client.post("/api/soc/alerts", json={"title": title, "severity": severity, "source": "iam"}).json()["id"]


def test_health_and_version(client):
    r = client.get("/health", headers={"X-Request-Id": "suite-test"})
    assert r.status_code == 200
    assert r.json()["version"] == VERSION


def test_alert_lifecycle(client):
    alert_id = _alert(client)
    assert client.get("/api/soc/alerts").json()["total"] == 1
    assert client.post(f"/api/soc/alerts/{alert_id}/ack").json()["status"] == "acknowledged"
    assert client.post(f"/api/soc/alerts/{alert_id}/resolve").json()["status"] == "resolved"
    assert client.post("/api/soc/alerts/nope/ack").status_code == 404


def test_alert_filters(client):
    _alert(client, severity="critical")
    _alert(client, severity="low")
    assert client.get("/api/soc/alerts", params={"severity": "critical"}).json()["total"] == 1


def test_playbook(client):
    assert client.post("/api/soc/playbooks", json={"name": "contain", "steps": ["隔离主机", "封禁 IP", "取证"]}).status_code == 201
    assert client.post("/api/soc/playbooks", json={"name": "contain", "steps": ["x"]}).status_code == 409
    assert client.get("/api/soc/playbooks").json()["total"] == 1


def test_incident_flow(client):
    a1 = _alert(client, severity="critical")
    pb = client.post("/api/soc/playbooks", json={"name": "ir", "steps": ["step1"]}).json()["id"]
    incident = client.post("/api/soc/incidents", json={"title": "重大安全事件", "severity": "critical", "alert_ids": [a1], "playbook_id": pb}).json()
    assert incident["status"] == "open"
    assert client.get("/api/soc/incidents").json()["total"] == 1
    assert client.post(f"/api/soc/incidents/{incident['id']}/resolve").json()["status"] == "resolved"
    assert client.get("/api/soc/incidents", params={"status_": "resolved"}).json()["total"] == 1


def test_stats(client):
    _alert(client, severity="critical")
    _alert(client, severity="high")
    stats = client.get("/api/soc/stats").json()
    assert stats["critical"] == 1
    assert stats["high"] == 1
    assert stats["alerts_open"] == 2


def test_manifest_and_crypto(client):
    assert client.get("/api/integration/manifest").json()["version"] == VERSION
    enc = client.post("/api/crypto/encrypt", json={"value": "x"}).json()["ciphertext"]
    assert client.post("/api/crypto/decrypt", json={"value": enc}).json()["plaintext"] == "x"


def test_write_requires_auth(client):
    del client.headers["X-Internal-Token"]
    assert client.post("/api/soc/alerts", json={"title": "x", "severity": "low", "source": "s"}).status_code == 401
