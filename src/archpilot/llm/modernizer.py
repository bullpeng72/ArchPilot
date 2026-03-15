"""현대화 설계 생성기 — LLM 기반 신규 시스템 아키텍처 생성."""

from __future__ import annotations

import json

from rich.console import Console

from archpilot.core.models import AnalysisResult, ModernizationScenario, SystemModel
from archpilot.core.parser import SystemParser
from archpilot.llm.client import LLMError, get_client
from archpilot.llm.prompts import (
    LLM_JSON_SUFFIX,
    MIGRATION_PLAN_PROMPT,
    MODERNIZE_SKELETON_PROMPT,
    MODERNIZE_SYSTEM_PROMPT,
)
from archpilot.llm.utils import (
    LARGE_SYSTEM_THRESHOLD,
    MAX_MODERNIZE_TOKENS,
    MAX_PLAN_SYSTEM_CHARS,
    MAX_PLAN_TOKENS,
    MAX_SKELETON_TOKENS,
    compress_analysis,
    compress_for_plan,
    compress_model,
)

_console = Console(stderr=True)

# A2 재시도 횟수 상한 (1 = 최초 시도 + 1회 교정)
_MAX_RETRY = 1


class SystemModernizer:
    # ── 공개 API ──────────────────────────────────────────────────────────────

    def modernize(
        self,
        legacy: SystemModel,
        requirements: str,
        analysis: AnalysisResult | None = None,
        scenario: ModernizationScenario | None = None,
    ) -> SystemModel:
        """레거시 시스템을 현대화한다.

        컴포넌트 수가 LARGE_SYSTEM_THRESHOLD 초과이면 2단계 분할(A3),
        이하이면 단일 패스 + A2 재시도를 적용한다.
        두 경로 모두 A1(체크리스트 주입)을 포함한다.
        """
        if len(legacy.components) > LARGE_SYSTEM_THRESHOLD:
            return self._modernize_two_phase(legacy, requirements, analysis, scenario)
        return self._modernize_single_pass(legacy, requirements, analysis, scenario)

    def generate_migration_plan(
        self,
        legacy: SystemModel,
        modern: SystemModel,
        analysis: AnalysisResult | None = None,
        requirements: str = "",
    ) -> str:
        client = get_client()

        legacy_payload = compress_for_plan(
            json.loads(legacy.model_dump_json()), max_chars=MAX_PLAN_SYSTEM_CHARS
        )
        modern_payload = compress_for_plan(
            json.loads(modern.model_dump_json()), max_chars=MAX_PLAN_SYSTEM_CHARS
        )

        user_message = (
            f"요구사항: {requirements}\n\n"
            f"레거시 시스템:\n{legacy_payload}\n\n"
            f"현대화 시스템:\n{modern_payload}"
        )
        if analysis:
            user_message += f"\n\n분석 결과:\n{compress_analysis(analysis)}"

        return client.chat(
            MIGRATION_PLAN_PROMPT,
            user_message,
            json_mode=False,
            max_tokens=MAX_PLAN_TOKENS,
        )

    # ── 내부 헬퍼 ─────────────────────────────────────────────────────────────

    def _resolve_scenario(
        self,
        scenario: ModernizationScenario | None,
        analysis: AnalysisResult | None,
    ) -> ModernizationScenario:
        return (
            scenario
            or (analysis.recommended_scenario if analysis else None)
            or ModernizationScenario.FULL_REPLACE
        )

    def _build_scenario_section(self, resolved: ModernizationScenario) -> str:
        return f"\n\nscenario: {resolved.value}\n시나리오 설명: {resolved.label}"

    def _build_analysis_section(
        self,
        analysis: AnalysisResult | None,
        resolved: ModernizationScenario,
    ) -> str:
        if not analysis:
            return ""
        decisions_json = json.dumps(
            [d.model_dump() for d in analysis.component_decisions],
            ensure_ascii=False,
            indent=2,
        )
        return (
            f"\n\n분석 결과 (시나리오: {resolved.value}):\n"
            f"추천 시나리오 근거: {analysis.scenario_rationale}\n"
            f"컴포넌트별 전략 결정:\n{decisions_json}\n"
            f"전체 분석:\n{compress_analysis(analysis)}"
        )

    def _build_component_checklist(
        self,
        legacy: SystemModel,
        analysis: AnalysisResult | None,
    ) -> tuple[str, list[str], set[str]]:
        """A1: 레거시 컴포넌트 체크리스트 생성.

        Returns:
            checklist: 포맷된 체크리스트 문자열 (id·type·action 한 줄씩)
            must_include_ids: retire 제외 처리 대상 컴포넌트 id 목록
            retire_ids: retire 대상 id 집합
        """
        decisions_by_id: dict[str, str] = {}
        retire_ids: set[str] = set()
        if analysis:
            legacy_ids = {c.id for c in legacy.components}
            stale_ids = []
            for d in analysis.component_decisions:
                decisions_by_id[d.component_id] = d.action.value
                if d.action.value == "retire":
                    retire_ids.add(d.component_id)
                if d.component_id not in legacy_ids:
                    stale_ids.append(d.component_id)
            if stale_ids:
                _console.print(
                    f"[yellow]⚠ 분석 결과의 component_decisions에 현재 시스템에 없는 "
                    f"ID {len(stale_ids)}개가 포함됩니다 (stale analysis): "
                    f"{stale_ids[:5]}{'...' if len(stale_ids) > 5 else ''}\n"
                    f"  → 해당 결정은 무시됩니다. 시스템 변경 후 재분석을 권장합니다.[/yellow]"
                )
                # stale ID는 decisions에서 제외 (잘못된 retire 판정 방지)
                for sid in stale_ids:
                    decisions_by_id.pop(sid, None)
                    retire_ids.discard(sid)

        lines = []
        for c in legacy.components:
            action = decisions_by_id.get(c.id, "")
            action_str = f" → {action}" if action else ""
            lines.append(f"  - {c.id} ({c.type.value}){action_str}")

        must_include_ids = [c.id for c in legacy.components if c.id not in retire_ids]
        return "\n".join(lines), must_include_ids, retire_ids

    def _check_missing(
        self,
        modern: SystemModel,
        must_include_ids: list[str],
    ) -> list[str]:
        modern_ids = {c.id for c in modern.components}
        return [id for id in must_include_ids if id not in modern_ids]

    # ── Single-pass (≤ LARGE_SYSTEM_THRESHOLD) — A1 + A2 ─────────────────────

    def _modernize_single_pass(
        self,
        legacy: SystemModel,
        requirements: str,
        analysis: AnalysisResult | None,
        scenario: ModernizationScenario | None,
    ) -> SystemModel:
        client = get_client()
        resolved = self._resolve_scenario(scenario, analysis)
        checklist, must_include_ids, retire_ids = self._build_component_checklist(
            legacy, analysis
        )
        retire_count = len(retire_ids)
        min_expected = max(1, len(legacy.components) - retire_count)

        # A1: 체크리스트 + 규모 어노테이션 주입
        user_message = (
            f"[레거시 규모: {len(legacy.components)}개 컴포넌트 — "
            f"retire {retire_count}개 제외 최소 {min_expected}개 출력]\n"
            f"[처리 대상 컴포넌트 목록 (빠짐없이 현대화 설계에 반영할 것)]:\n"
            f"{checklist}\n\n"
            f"현대화 요구사항:\n{requirements}"
            f"{self._build_scenario_section(resolved)}"
            f"{self._build_analysis_section(analysis, resolved)}"
            f"\n\nLegacy 시스템:\n{compress_model(legacy)}"
        )

        # A2: 재시도 루프
        missing: list[str] = []
        modern: SystemModel | None = None
        for attempt in range(_MAX_RETRY + 1):
            if attempt == 0:
                msg = user_message
            else:
                msg = (
                    f"[재설계 요청 — {attempt}차 교정]\n"
                    f"이전 응답에서 다음 {len(missing)}개 컴포넌트가 누락됐습니다:\n"
                    + "\n".join(f"  - {id}" for id in missing)
                    + "\n\n위 컴포넌트를 반드시 포함하여 전체 아키텍처를 재설계하십시오.\n\n"
                    + user_message
                )

            data = client.chat_json(
                MODERNIZE_SYSTEM_PROMPT, msg, max_tokens=MAX_MODERNIZE_TOKENS
            )
            try:
                modern = SystemParser()._dict_to_model(data)
            except Exception as e:
                raise LLMError(f"현대화 시스템 모델 파싱 실패: {e}") from e

            missing = self._check_missing(modern, must_include_ids)
            if not missing:
                break

            if attempt == _MAX_RETRY:
                _console.print(
                    f"[yellow]⚠ {_MAX_RETRY}차 재시도 후에도 {len(missing)}개 컴포넌트 누락: "
                    f"{missing[:5]}{'...' if len(missing) > 5 else ''}[/yellow]"
                )
                # 누락 정보를 metadata에 기록하여 상위 레이어가 경고를 표시할 수 있게 함
                modern = modern.model_copy(
                    update={"metadata": {**modern.metadata, "_missing_components": missing}}
                )

        return modern  # type: ignore[return-value]

    # ── Two-phase (> LARGE_SYSTEM_THRESHOLD) — A1 + A3 ───────────────────────

    def _modernize_two_phase(
        self,
        legacy: SystemModel,
        requirements: str,
        analysis: AnalysisResult | None,
        scenario: ModernizationScenario | None,
    ) -> SystemModel:
        _console.print(
            f"[cyan]ℹ 대형 시스템 ({len(legacy.components)}개 컴포넌트) — "
            f"2단계 현대화 적용 (임계값: {LARGE_SYSTEM_THRESHOLD}개)[/cyan]"
        )
        resolved = self._resolve_scenario(scenario, analysis)
        skeleton = self._generate_skeleton(legacy, analysis, resolved)
        return self._enrich_skeleton(skeleton, legacy, requirements, analysis)

    def _generate_skeleton(
        self,
        legacy: SystemModel,
        analysis: AnalysisResult | None,
        resolved: ModernizationScenario,
    ) -> dict:
        """Phase 1: 컴포넌트 목록 스켈레톤 생성 (connections 없음)."""
        client = get_client()
        checklist, must_include_ids, retire_ids = self._build_component_checklist(
            legacy, analysis
        )

        decisions_section = ""
        if analysis:
            decisions_json = json.dumps(
                [d.model_dump() for d in analysis.component_decisions],
                ensure_ascii=False,
                indent=2,
            )
            decisions_section = f"\n\ncomponent_decisions:\n{decisions_json}"

        skeleton_msg = (
            f"시나리오: {resolved.value}\n"
            f"레거시 컴포넌트 수: {len(legacy.components)}개 "
            f"(retire {len(retire_ids)}개 제외 → 최소 {len(must_include_ids)}개 필요)\n\n"
            f"처리해야 할 레거시 컴포넌트 목록 (빠짐없이 처리할 것):\n{checklist}"
            f"{decisions_section}"
        )

        skeleton = client.chat_json(
            MODERNIZE_SKELETON_PROMPT, skeleton_msg, max_tokens=MAX_SKELETON_TOKENS
        )
        actual = len(skeleton.get("components", []))
        _console.print(
            f"[cyan]  Phase 1 완료: 스켈레톤 {actual}개 / 최소 {len(must_include_ids)}개[/cyan]"
        )
        return skeleton

    def _enrich_skeleton(
        self,
        skeleton: dict,
        legacy: SystemModel,
        requirements: str,
        analysis: AnalysisResult | None,
    ) -> SystemModel:
        """Phase 2: 스켈레톤에 tech/criticality/metadata 추가 + connections 생성."""
        client = get_client()

        skeleton_json = json.dumps(skeleton, ensure_ascii=False, indent=2)
        legacy_conns_json = json.dumps(
            [json.loads(c.model_dump_json()) for c in legacy.connections],
            ensure_ascii=False,
            indent=2,
        )
        analysis_section = ""
        if analysis:
            analysis_section = f"\n\n분석 결과:\n{compress_analysis(analysis)}"

        enrich_msg = (
            f"[2단계: 스켈레톤 확장]\n"
            f"아래 컴포넌트 스켈레톤의 각 항목에 tech·criticality·lifecycle_status·"
            f"data_classification·metadata를 추가하고,\n"
            f"레거시 connections를 현대화하여 connections 배열을 생성하라.\n"
            f"컴포넌트 id 목록은 변경하지 말 것 (추가는 가능, 삭제·id 변경 불가).\n\n"
            f"확정된 컴포넌트 스켈레톤 ({len(skeleton.get('components', []))}개):\n"
            f"{skeleton_json}\n\n"
            f"레거시 connections (현대화된 연결 설계에 활용):\n{legacy_conns_json}\n\n"
            f"요구사항: {requirements}"
            f"{analysis_section}"
        )

        data = client.chat_json(
            MODERNIZE_SYSTEM_PROMPT + LLM_JSON_SUFFIX,
            enrich_msg,
            max_tokens=MAX_MODERNIZE_TOKENS,
        )
        try:
            modern = SystemParser()._dict_to_model(data)
        except Exception as e:
            raise LLMError(f"현대화 시스템 모델 파싱 실패: {e}") from e

        _console.print(
            f"[cyan]  Phase 2 완료: {len(modern.components)}개 컴포넌트, "
            f"{len(modern.connections)}개 연결[/cyan]"
        )
        return modern
