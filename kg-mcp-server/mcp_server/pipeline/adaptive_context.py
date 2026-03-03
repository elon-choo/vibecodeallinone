"""
Conversation-Aware Adaptive Context (Phase 5.2)
================================================
세션 내 대화 흐름을 추적하여 점진적 컨텍스트 적응.

핵심 기능:
1. Session Memory Graph: 세션 내 언급된 엔티티를 추적
2. Progressive Narrowing: 대화 진행 시 컨텍스트 범위 자동 축소
3. Intent Transition Detection: IMPLEMENT→TEST→DEPLOY 전환 감지
4. Deduplication: 이미 주입된 컨텍스트 재주입 방지
"""

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

ANALYTICS_DIR = Path.home() / ".claude" / "mcp-kg-analytics"
ANALYTICS_DIR.mkdir(parents=True, exist_ok=True)
CONVERSATION_STATE_FILE = ANALYTICS_DIR / "conversation_state.json"

# 대화 비활성 타임아웃 (30분)
CONVERSATION_TIMEOUT = 1800


class ConversationMemory:
    """대화 흐름을 추적하는 세션 메모리.

    프로젝트 디렉토리 기준으로 대화를 식별하며,
    30분 비활성 시 자동으로 새 대화로 리셋.
    """

    def __init__(self, project_dir: str = ""):
        self.project_dir = project_dir
        self.state = self._load_or_create()

    def _load_or_create(self) -> Dict[str, Any]:
        """기존 상태 로드 또는 새로 생성."""
        try:
            if CONVERSATION_STATE_FILE.exists():
                data = json.loads(CONVERSATION_STATE_FILE.read_text(encoding="utf-8"))
                # 같은 프로젝트 + 타임아웃 미초과 시에만 복원
                if (data.get("project_dir") == self.project_dir
                        and time.time() - data.get("last_active", 0) < CONVERSATION_TIMEOUT):
                    return data
        except Exception as e:
            logger.debug(f"Failed to load conversation state: {e}")
        return self._new_state()

    def _new_state(self) -> Dict[str, Any]:
        return {
            "project_dir": self.project_dir,
            "conversation_id": f"conv_{int(time.time())}",
            "started_at": datetime.utcnow().isoformat() + "Z",
            "last_active": time.time(),
            "turn_count": 0,
            "intent_history": [],       # [{"intent": "IMPLEMENT", "target": "foo", "ts": ...}, ...]
            "mentioned_entities": {},   # {"entity_name": {"count": N, "first_turn": M, "last_turn": M, "type": "..."}}
            "injected_nodes": [],       # 이미 주입된 노드 이름 (중복 방지)
            "focus_scope": None,        # 현재 집중 범위 (module/class 이름)
            "narrowing_level": 0,       # 0=broad, 1=module, 2=class, 3=function
        }

    def save(self):
        """상태를 디스크에 저장."""
        self.state["last_active"] = time.time()
        try:
            CONVERSATION_STATE_FILE.write_text(
                json.dumps(self.state, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
        except Exception as e:
            logger.warning(f"Failed to save conversation state: {e}")

    def update_turn(self, intent: str, target: Optional[str],
                    keywords: List[str], injected_names: List[str]):
        """새 턴(프롬프트)의 정보로 대화 상태 업데이트.

        Args:
            intent: 분류된 의도 (IMPLEMENT, TEST, DEBUG 등)
            target: 대상 식별자 (함수/클래스명)
            keywords: 감지된 키워드 목록
            injected_names: 이번 턴에 주입된 노드 이름 목록
        """
        self.state["turn_count"] += 1
        turn = self.state["turn_count"]

        # Intent 히스토리 기록
        self.state["intent_history"].append({
            "intent": intent,
            "target": target,
            "turn": turn,
            "ts": datetime.utcnow().isoformat() + "Z",
        })
        # 최근 20턴만 유지
        if len(self.state["intent_history"]) > 20:
            self.state["intent_history"] = self.state["intent_history"][-20:]

        # 엔티티 추적
        entities = set()
        if target:
            entities.add(target)
        entities.update(kw for kw in keywords if len(kw) > 2 and kw not in (
            "code", "코드", "확인", "check", "추가", "add", "code_file", "code_block"
        ))

        for entity in entities:
            if entity in self.state["mentioned_entities"]:
                entry = self.state["mentioned_entities"][entity]
                entry["count"] += 1
                entry["last_turn"] = turn
            else:
                self.state["mentioned_entities"][entity] = {
                    "count": 1,
                    "first_turn": turn,
                    "last_turn": turn,
                    "type": "target" if entity == target else "keyword",
                }

        # 주입된 노드 기록 (중복 방지용)
        for name in injected_names:
            if name not in self.state["injected_nodes"]:
                self.state["injected_nodes"].append(name)
        # 최근 50개만 유지
        if len(self.state["injected_nodes"]) > 50:
            self.state["injected_nodes"] = self.state["injected_nodes"][-50:]

        # Progressive Narrowing 업데이트
        self._update_narrowing(intent, target)

        self.save()

    def _update_narrowing(self, intent: str, target: Optional[str]):
        """대화 진행에 따른 컨텍스트 범위 자동 축소."""
        turn = self.state["turn_count"]

        if turn <= 1:
            # 첫 턴: 넓은 범위
            self.state["narrowing_level"] = 0
            if target:
                self.state["focus_scope"] = target
        elif turn <= 3:
            # 2-3턴: 모듈 수준으로 좁힘
            self.state["narrowing_level"] = 1
            if target:
                self.state["focus_scope"] = target
        else:
            # 4턴+: 함수/클래스 수준으로 집중
            self.state["narrowing_level"] = min(3, self.state["narrowing_level"] + 1)
            if target:
                self.state["focus_scope"] = target

    def detect_intent_transition(self) -> Optional[Dict[str, str]]:
        """Intent 전환 감지. 최근 2턴의 intent가 다르면 전환으로 판단.

        Returns:
            {"from": "IMPLEMENT", "to": "TEST"} 또는 None
        """
        history = self.state["intent_history"]
        if len(history) < 2:
            return None

        prev = history[-2]["intent"]
        curr = history[-1]["intent"]
        if prev != curr:
            return {"from": prev, "to": curr}
        return None

    def get_search_refinement(self) -> Dict[str, Any]:
        """현재 대화 상태 기반 검색 최적화 힌트 반환.

        Returns:
            {
                "boost_entities": [...],      # 가중치 높일 엔티티
                "suppress_entities": [...],   # 이미 충분히 노출된 엔티티
                "focus_scope": "...",          # 집중할 범위
                "max_items": N,               # 축소된 결과 수
                "already_injected": [...],    # 중복 방지용
            }
        """
        entities = self.state["mentioned_entities"]
        turn = self.state["turn_count"]

        # Boost: 최근 2턴 내에 반복 언급된 엔티티
        boost = [
            name for name, info in entities.items()
            if info["count"] >= 2 and info["last_turn"] >= turn - 1
        ]

        # Suppress: 3번 이상 주입되었고 마지막 언급이 3턴 이상 전인 엔티티
        suppress = [
            name for name, info in entities.items()
            if info["count"] >= 3 and info["last_turn"] < turn - 2
        ]

        # Progressive Narrowing에 따른 결과 수 조정
        level = self.state["narrowing_level"]
        max_items_map = {0: 7, 1: 5, 2: 4, 3: 3}
        max_items = max_items_map.get(level, 5)

        return {
            "boost_entities": boost[:5],
            "suppress_entities": suppress[:5],
            "focus_scope": self.state["focus_scope"],
            "narrowing_level": level,
            "max_items": max_items,
            "already_injected": self.state["injected_nodes"][-20:],
            "turn_count": turn,
        }

    def get_context_summary(self) -> Dict[str, Any]:
        """MCP 도구용: 현재 대화 컨텍스트 요약 반환."""
        entities = self.state["mentioned_entities"]
        history = self.state["intent_history"]

        # 핵심 엔티티 (언급 빈도순)
        top_entities = sorted(
            entities.items(),
            key=lambda x: x[1]["count"],
            reverse=True,
        )[:10]

        # Intent 전환 감지
        transition = self.detect_intent_transition()

        return {
            "conversation_id": self.state["conversation_id"],
            "turn_count": self.state["turn_count"],
            "focus_scope": self.state["focus_scope"],
            "narrowing_level": self.state["narrowing_level"],
            "top_entities": [
                {"name": name, "count": info["count"], "type": info["type"]}
                for name, info in top_entities
            ],
            "intent_flow": [h["intent"] for h in history[-5:]],
            "current_intent": history[-1]["intent"] if history else None,
            "intent_transition": transition,
            "total_injected": len(self.state["injected_nodes"]),
        }

    def reset(self):
        """대화 상태 초기화."""
        self.state = self._new_state()
        self.save()
