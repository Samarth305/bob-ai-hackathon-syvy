"""
test_api_health.py — Integration tests for GET /health

Covers:
  - 200 OK response
  - response body has status and version fields
  - status == "ok"
"""

import pytest


class TestHealthEndpoint:
    def test_returns_200(self, api_client):
        resp = api_client.get("/health")
        assert resp.status_code == 200

    def test_response_body_has_status(self, api_client):
        resp = api_client.get("/health")
        data = resp.json()
        assert "status" in data

    def test_response_body_has_version(self, api_client):
        resp = api_client.get("/health")
        data = resp.json()
        assert "version" in data

    def test_status_is_ok(self, api_client):
        resp = api_client.get("/health")
        assert resp.json()["status"] == "ok"

    def test_version_is_string(self, api_client):
        resp = api_client.get("/health")
        assert isinstance(resp.json()["version"], str)

    def test_content_type_is_json(self, api_client):
        resp = api_client.get("/health")
        assert "application/json" in resp.headers["content-type"]
