"""SOC 业务深化测试：告警 / 安全事件 / 处置记录。"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app

INTERNAL_TOKEN = "test-internal-key-12345"
AUTH_HEADERS = {"X-Internal-Token": INTERNAL_TOKEN}


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


# ═══════════════════════════════════════════════════════════
# 告警管理
# ═══════════════════════════════════════════════════════════
class TestAlertManagement:
    def test_create_alert_success(self, client):
        resp = client.post("/api/soc/alerts", json={
            "source": "ids", "title": "SSH 暴力破解", "severity": "critical",
            "host": "web-01", "description": "短时间多次失败登录",
        }, headers=AUTH_HEADERS)
        assert resp.status_code == 201
        data = resp.json()
        assert data["severity"] == "critical"
        assert data["status"] == "active"
        assert data["incident_id"] == ""

    def test_create_alert_requires_token(self, client):
        resp = client.post("/api/soc/alerts", json={
            "title": "无令牌告警", "severity": "low",
        })
        assert resp.status_code in (401, 403)

    def test_list_alerts(self, client):
        resp = client.get("/api/soc/alerts", headers=AUTH_HEADERS)
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    def test_filter_by_severity(self, client):
        resp = client.get("/api/soc/alerts?severity=critical", headers=AUTH_HEADERS)
        assert resp.status_code == 200
        for item in resp.json()["items"]:
            assert item["severity"] == "critical"

    def test_keyword_search(self, client):
        resp = client.get("/api/soc/alerts?keyword=SSH", headers=AUTH_HEADERS)
        assert resp.status_code == 200
        titles = [a["title"] for a in resp.json()["items"]]
        assert any("SSH" in t for t in titles)

    def test_get_alert(self, client):
        list_resp = client.get("/api/soc/alerts?keyword=SSH", headers=AUTH_HEADERS)
        alert_id = list_resp.json()["items"][0]["id"]
        resp = client.get(f"/api/soc/alerts/{alert_id}", headers=AUTH_HEADERS)
        assert resp.status_code == 200
        assert resp.json()["id"] == alert_id

    def test_get_alert_not_found(self, client):
        resp = client.get("/api/soc/alerts/nonexistent-id", headers=AUTH_HEADERS)
        assert resp.status_code == 404

    def test_change_alert_status(self, client):
        list_resp = client.get("/api/soc/alerts?keyword=SSH", headers=AUTH_HEADERS)
        alert_id = list_resp.json()["items"][0]["id"]
        resp = client.patch(f"/api/soc/alerts/{alert_id}/status",
                            json={"status": "acknowledged"}, headers=AUTH_HEADERS)
        assert resp.status_code == 200
        assert resp.json()["status"] == "acknowledged"


# ═══════════════════════════════════════════════════════════
# 安全事件
# ═══════════════════════════════════════════════════════════
class TestIncidentManagement:
    def test_create_incident_success(self, client):
        resp = client.post("/api/soc/incidents", json={
            "title": "可疑横向移动", "severity": "high",
            "owner": "soc-oncall", "description": "内网异常 RDP",
        }, headers=AUTH_HEADERS)
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "open"
        assert data["severity"] == "high"

    def test_create_incident_requires_token(self, client):
        resp = client.post("/api/soc/incidents", json={"title": "无令牌事件"})
        assert resp.status_code in (401, 403)

    def test_list_incidents(self, client):
        resp = client.get("/api/soc/incidents", headers=AUTH_HEADERS)
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    def test_filter_incidents_by_severity(self, client):
        resp = client.get("/api/soc/incidents?severity=high", headers=AUTH_HEADERS)
        assert resp.status_code == 200
        for item in resp.json()["items"]:
            assert item["severity"] == "high"

    def test_get_incident_not_found(self, client):
        resp = client.get("/api/soc/incidents/nonexistent-id", headers=AUTH_HEADERS)
        assert resp.status_code == 404

    def test_update_incident(self, client):
        list_resp = client.get("/api/soc/incidents?keyword=横向", headers=AUTH_HEADERS)
        incident_id = list_resp.json()["items"][0]["id"]
        resp = client.patch(f"/api/soc/incidents/{incident_id}", json={
            "owner": "new-oncall", "description": "更新后的描述",
        }, headers=AUTH_HEADERS)
        assert resp.status_code == 200
        assert resp.json()["owner"] == "new-oncall"

    def test_full_incident_status_machine(self, client):
        list_resp = client.get("/api/soc/incidents?keyword=横向", headers=AUTH_HEADERS)
        incident_id = list_resp.json()["items"][0]["id"]
        for nxt in ["investigating", "contained", "closed"]:
            r = client.patch(f"/api/soc/incidents/{incident_id}/status",
                             json={"status": nxt}, headers=AUTH_HEADERS)
            assert r.status_code == 200
            assert r.json()["status"] == nxt

    def test_illegal_incident_transition(self, client):
        list_resp = client.get("/api/soc/incidents?keyword=横向", headers=AUTH_HEADERS)
        incident_id = list_resp.json()["items"][0]["id"]
        # 已 closed，禁止回退
        resp = client.patch(f"/api/soc/incidents/{incident_id}/status",
                            json={"status": "open"}, headers=AUTH_HEADERS)
        assert resp.status_code == 409


# ═══════════════════════════════════════════════════════════
# 告警关联事件 + 处置记录
# ═══════════════════════════════════════════════════════════
class TestAssociationAndResponse:
    def _make_open_incident(self, client, title="待关联事件") -> str:
        resp = client.post("/api/soc/incidents", json={
            "title": title, "severity": "medium",
        }, headers=AUTH_HEADERS)
        return resp.json()["id"]

    def _make_alert(self, client, title="待关联告警") -> str:
        resp = client.post("/api/soc/alerts", json={
            "title": title, "severity": "medium",
        }, headers=AUTH_HEADERS)
        return resp.json()["id"]

    def test_associate_alert_to_incident(self, client):
        incident_id = self._make_open_incident(client)
        alert_id = self._make_alert(client)
        resp = client.post(f"/api/soc/alerts/{alert_id}/associate",
                           json={"incident_id": incident_id}, headers=AUTH_HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert data["incident_id"] == incident_id
        assert data["status"] == "acknowledged"

    def test_associate_nonexistent_incident(self, client):
        alert_id = self._make_alert(client)
        resp = client.post(f"/api/soc/alerts/{alert_id}/associate",
                           json={"incident_id": "missing"}, headers=AUTH_HEADERS)
        assert resp.status_code == 404

    def test_filter_alerts_by_incident(self, client):
        incident_id = self._make_open_incident(client, "过滤关联事件")
        alert_id = self._make_alert(client, "过滤关联告警")
        client.post(f"/api/soc/alerts/{alert_id}/associate",
                    json={"incident_id": incident_id}, headers=AUTH_HEADERS)
        resp = client.get(f"/api/soc/alerts?incident_id={incident_id}", headers=AUTH_HEADERS)
        assert resp.status_code == 200
        for a in resp.json()["items"]:
            assert a["incident_id"] == incident_id

    def test_create_response(self, client):
        incident_id = self._make_open_incident(client, "处置事件")
        resp = client.post(f"/api/soc/incidents/{incident_id}/responses", json={
            "action": "隔离受影响主机", "operator": "analyst01", "note": "已断网",
        }, headers=AUTH_HEADERS)
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "pending"
        assert data["incident_id"] == incident_id

    def test_create_response_nonexistent_incident(self, client):
        resp = client.post("/api/soc/incidents/missing/responses", json={
            "action": "孤儿处置",
        }, headers=AUTH_HEADERS)
        assert resp.status_code == 404

    def test_list_responses(self, client):
        incident_id = self._make_open_incident(client, "列处置事件")
        client.post(f"/api/soc/incidents/{incident_id}/responses", json={
            "action": "封禁 IP",
        }, headers=AUTH_HEADERS)
        resp = client.get(f"/api/soc/incidents/{incident_id}/responses", headers=AUTH_HEADERS)
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    def test_response_flow_completed(self, client):
        incident_id = self._make_open_incident(client, "完成处置事件")
        create_resp = client.post(f"/api/soc/incidents/{incident_id}/responses", json={
            "action": "查杀病毒",
        }, headers=AUTH_HEADERS)
        response_id = create_resp.json()["id"]
        resp = client.patch(f"/api/soc/responses/{response_id}/status",
                             json={"status": "completed"}, headers=AUTH_HEADERS)
        assert resp.status_code == 200
        assert resp.json()["status"] == "completed"

    def test_response_flow_failed(self, client):
        incident_id = self._make_open_incident(client, "失败处置事件")
        create_resp = client.post(f"/api/soc/incidents/{incident_id}/responses", json={
            "action": "回滚变更",
        }, headers=AUTH_HEADERS)
        response_id = create_resp.json()["id"]
        resp = client.patch(f"/api/soc/responses/{response_id}/status",
                            json={"status": "failed"}, headers=AUTH_HEADERS)
        assert resp.status_code == 200
        assert resp.json()["status"] == "failed"

    def test_illegal_response_transition(self, client):
        incident_id = self._make_open_incident(client, "非法处置事件")
        create_resp = client.post(f"/api/soc/incidents/{incident_id}/responses", json={
            "action": "重启服务",
        }, headers=AUTH_HEADERS)
        response_id = create_resp.json()["id"]
        # pending -> completed 先完成
        client.patch(f"/api/soc/responses/{response_id}/status",
                     json={"status": "completed"}, headers=AUTH_HEADERS)
        # completed 不可再回 pending
        bad = client.patch(f"/api/soc/responses/{response_id}/status",
                           json={"status": "pending"}, headers=AUTH_HEADERS)
        assert bad.status_code == 409
