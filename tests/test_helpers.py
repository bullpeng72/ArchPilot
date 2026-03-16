"""tests/test_helpers.py — ui/helpers.py 유닛 테스트."""

from __future__ import annotations

import json
import logging

import pytest

from archpilot.ui.helpers import (
    _best_id_match,
    _clean_json,
    _repair_connections,
    _token_match_score,
)


# ── _token_match_score ────────────────────────────────────────────────────────

class TestTokenMatchScore:
    def test_exact_token_match(self):
        assert _token_match_score("order_service", "order_service_new") == 1

    def test_multiple_token_match(self):
        assert _token_match_score("order_payment_service", "order_payment_api") == 2

    def test_no_match(self):
        assert _token_match_score("redis_cache", "postgres_db") == 0

    def test_only_common_tokens_ignored(self):
        # "new", "service" 등 공통 토큰만 겹치면 0 반환
        assert _token_match_score("new_service", "old_service") == 0

    def test_empty_after_common_removal(self):
        # 의미 토큰이 없으면 0
        assert _token_match_score("new", "old") == 0

    def test_case_insensitive(self):
        assert _token_match_score("Order_SVC", "order_svc_v2") == 1


# ── _best_id_match ────────────────────────────────────────────────────────────

class TestBestIdMatch:
    def test_exact_match_preferred(self):
        valid = {"order_service", "payment_service", "user_service"}
        assert _best_id_match("order_service", valid) == "order_service"

    def test_token_match_found(self):
        valid = {"order_svc_new", "payment_svc", "user_svc"}
        result = _best_id_match("order_svc_legacy", valid)
        assert result == "order_svc_new"

    def test_no_match_returns_none(self):
        valid = {"redis_cache", "postgres_db"}
        assert _best_id_match("kafka_broker", valid) == None  # noqa: E711

    def test_shorter_id_preferred_on_tie(self):
        # 동점 시 더 짧은 id 선택
        valid = {"order_svc", "order_svc_extended"}
        result = _best_id_match("order_api", valid)
        assert result == "order_svc"

    def test_minimum_one_token_required(self):
        # 토큰 겹침이 0이면 None
        valid = {"alpha_beta", "gamma_delta"}
        assert _best_id_match("zeta_eta", valid) == None  # noqa: E711

    def test_empty_valid_set(self):
        assert _best_id_match("order_service", set()) == None  # noqa: E711


# ── _repair_connections ───────────────────────────────────────────────────────

class TestRepairConnections:
    def _make_system(self, comp_ids: list[str], connections: list[dict]) -> dict:
        return {
            "components": [{"id": cid, "type": "service"} for cid in comp_ids],
            "connections": connections,
        }

    def test_all_valid_ids_unchanged(self):
        system = self._make_system(
            ["svc_a", "svc_b"],
            [{"from": "svc_a", "to": "svc_b", "protocol": "HTTP"}],
        )
        result = _repair_connections(system)
        assert result["connections"] == system["connections"]

    def test_replaces_map_priority_1(self):
        """metadata.replaces 역매핑 우선순위 검증."""
        system = {
            "components": [
                {"id": "order_svc_new", "type": "service",
                 "metadata": {"replaces": "order_svc_old"}},
                {"id": "payment_svc", "type": "service"},
            ],
            "connections": [
                {"from": "order_svc_old", "to": "payment_svc"},
            ],
        }
        result = _repair_connections(system)
        assert result["connections"][0]["from"] == "order_svc_new"

    def test_token_similarity_priority_2(self):
        """토큰 유사도 매핑 검증."""
        system = self._make_system(
            ["order_svc_new", "payment_svc"],
            [{"from": "order_svc_legacy", "to": "payment_svc"}],
        )
        result = _repair_connections(system)
        assert result["connections"][0]["from"] == "order_svc_new"

    def test_unrepairable_connection_preserved(self):
        """복구 불가 연결은 그대로 보존 (parser가 나중에 drop)."""
        system = self._make_system(
            ["alpha_svc"],
            [{"from": "completely_unknown_xyz", "to": "alpha_svc"}],
        )
        result = _repair_connections(system)
        assert result["connections"][0]["from"] == "completely_unknown_xyz"

    def test_from_id_field_normalized(self):
        """from_id / to_id 키 → from / to 키로 정규화."""
        system = {
            "components": [
                {"id": "order_svc_new", "type": "service",
                 "metadata": {"replaces": "order_old"}},
                {"id": "payment_svc", "type": "service"},
            ],
            "connections": [
                {"from_id": "order_old", "to_id": "payment_svc"},
            ],
        }
        result = _repair_connections(system)
        conn = result["connections"][0]
        assert "from_id" not in conn
        assert "to_id" not in conn
        assert conn["from"] == "order_svc_new"

    def test_no_connections_returns_unchanged(self):
        system = self._make_system(["svc_a"], [])
        result = _repair_connections(system)
        assert result["connections"] == []

    def test_empty_components(self):
        system = {"components": [], "connections": [{"from": "x", "to": "y"}]}
        result = _repair_connections(system)
        # 유효 id 없으므로 연결 그대로
        assert result["connections"][0]["from"] == "x"

    def test_logging_called_on_repair(self, caplog):
        system = self._make_system(
            ["order_svc_new", "payment_svc"],
            [{"from": "order_svc_legacy", "to": "payment_svc"}],
        )
        with caplog.at_level(logging.INFO, logger="archpilot.server"):
            _repair_connections(system)
        assert any("토큰매핑" in r.message or "connection" in r.message.lower()
                   for r in caplog.records)

    def test_multiple_connections_repaired(self):
        system = {
            "components": [
                {"id": "order_new", "type": "service", "metadata": {"replaces": "order_old"}},
                {"id": "pay_new", "type": "service", "metadata": {"replaces": "pay_old"}},
            ],
            "connections": [
                {"from": "order_old", "to": "pay_old"},
                {"from": "order_old", "to": "pay_new"},
            ],
        }
        result = _repair_connections(system)
        assert result["connections"][0]["from"] == "order_new"
        assert result["connections"][0]["to"] == "pay_new"
        assert result["connections"][1]["from"] == "order_new"


# ── _clean_json ───────────────────────────────────────────────────────────────

class TestCleanJson:
    def test_strips_markdown_fence(self):
        raw = '```json\n{"key": "value"}\n```'
        assert json.loads(_clean_json(raw)) == {"key": "value"}

    def test_strips_bare_fence(self):
        raw = '```\n{"key": "value"}\n```'
        assert json.loads(_clean_json(raw)) == {"key": "value"}

    def test_extracts_json_from_text(self):
        raw = 'Here is the result:\n{"key": "value"}\nEnd.'
        assert json.loads(_clean_json(raw)) == {"key": "value"}

    def test_removes_trailing_comma(self):
        raw = '{"a": 1, "b": 2,}'
        assert json.loads(_clean_json(raw)) == {"a": 1, "b": 2}

    def test_removes_trailing_comma_in_array(self):
        raw = '{"items": [1, 2, 3,]}'
        assert json.loads(_clean_json(raw)) == {"items": [1, 2, 3]}

    def test_escapes_literal_newline_in_string(self):
        # LLM이 문자열 안에 리터럴 줄바꿈을 넣는 경우
        raw = '{"desc": "line1\nline2"}'
        result = json.loads(_clean_json(raw))
        assert "line1" in result["desc"]

    def test_plain_json_unchanged(self):
        raw = '{"a": 1}'
        assert json.loads(_clean_json(raw)) == {"a": 1}

    def test_nested_object(self):
        raw = '```json\n{"outer": {"inner": [1, 2, 3]}}\n```'
        result = json.loads(_clean_json(raw))
        assert result["outer"]["inner"] == [1, 2, 3]
