"""
LLM-as-Judge: Gemini Flash 기반 코드 품질 자동 평가 시스템

Phase 6.6: AI 코드 리뷰어
- Gemini 2.0 Flash로 코드 품질을 1-5 스케일로 평가
- 정확성, 보안, 가독성, 테스트 가능성 4개 기준
- 평가 이력을 Neo4j에 EVALUATED_BY 엣지로 저장
"""

import json
import os
import re
import uuid
from typing import Dict, List, Optional

import logging

from google import genai
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# ~/.claude/power-pack.env에서 API 키 로드 (fallback: ~/.env)
_env_file = os.path.expanduser("~/.claude/power-pack.env")
if not os.path.exists(_env_file):
    _env_file = os.path.expanduser("~/.env")
load_dotenv(_env_file)
_gemini_client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))


EVALUATION_PROMPT = """You are a senior code reviewer. Evaluate the following code on a 1-5 scale.

Code:
{code}

Context (if available):
{context}

Evaluate on these criteria (each 1-5):
1. Correctness: Does the code do what it's supposed to?
2. Security: Are there any security vulnerabilities?
3. Readability: Is the code clean and easy to understand?
4. Testability: Is the code easy to test?

Respond in JSON format ONLY (no markdown fences, no extra text):
{{
  "overall_score": <1-5>,
  "criteria": {{
    "correctness": <1-5>,
    "security": <1-5>,
    "readability": <1-5>,
    "testability": <1-5>
  }},
  "feedback": "<specific feedback text>",
  "suggestions": ["<suggestion 1>", "<suggestion 2>"]
}}"""


class LLMJudge:
    """Gemini Flash 기반 코드 품질 자동 평가기."""

    def __init__(self, driver):
        """
        Args:
            driver: Neo4j driver 인스턴스
        """
        self.driver = driver
        self.model_name = "gemini-3-flash-preview"

    def evaluate_code(
        self, file_path: Optional[str] = None, code_snippet: Optional[str] = None
    ) -> Dict:
        """코드 품질 평가.

        file_path가 주어지면 파일을 읽어서 평가하고,
        code_snippet이 주어지면 직접 평가한다.

        Args:
            file_path: 평가할 파일 경로
            code_snippet: 평가할 코드 스니펫 (file_path 대신 직접 코드 전달)

        Returns:
            평가 결과 딕셔너리
        """
        code = code_snippet or ""

        # file_path가 주어지면 파일에서 코드 읽기
        if file_path and not code:
            try:
                expanded = os.path.realpath(os.path.expanduser(file_path))
                cwd = os.path.realpath(os.getcwd())
                if not expanded.startswith(cwd + os.sep) and expanded != cwd:
                    return {"success": False, "error": f"Path not allowed (outside working directory): {file_path}"}
                with open(expanded, "r", encoding="utf-8") as f:
                    code = f.read()
            except FileNotFoundError:
                return {"success": False, "error": f"File not found: {file_path}"}
            except Exception as e:
                return {"success": False, "error": f"Failed to read file: {e}"}

        if not code.strip():
            return {"success": False, "error": "No code provided. Supply file_path or code_snippet."}

        # 코드가 너무 길면 잘라내기 (Gemini Flash 토큰 제한 고려)
        max_chars = 30000
        truncated = False
        if len(code) > max_chars:
            code = code[:max_chars]
            truncated = True

        try:
            response_text = self._call_gemini(
                EVALUATION_PROMPT.format(code=code, context="N/A")
            )
            result = self._parse_evaluation(response_text)
        except Exception as e:
            return {"success": False, "error": f"Gemini API call failed: {e}"}

        if not result:
            return {
                "success": False,
                "error": "Failed to parse evaluation response from Gemini.",
                "raw_response": response_text[:500] if response_text else "",
            }

        eval_id = str(uuid.uuid4())
        effective_path = file_path or "snippet"

        # Neo4j에 평가 이력 저장
        try:
            self._save_evaluation(
                file_path=effective_path,
                score=result["overall_score"],
                feedback=result.get("feedback", ""),
                criteria_scores=result.get("criteria", {}),
                eval_id=eval_id,
            )
        except Exception as e:
            # 저장 실패해도 평가 결과는 반환
            result["neo4j_save_error"] = str(e)

        # Phase 6.7: Auto-feedback to weight_learner
        try:
            self._auto_feedback(result, effective_path)
        except Exception as e:
            logger.debug(f"Auto-feedback skipped: {e}")

        return {
            "success": True,
            "file_path": effective_path,
            "overall_score": result["overall_score"],
            "criteria": result.get("criteria", {}),
            "feedback": result.get("feedback", ""),
            "suggestions": result.get("suggestions", []),
            "eval_id": eval_id,
            "truncated": truncated,
        }

    def evaluate_with_context(self, code: str, context: str) -> Dict:
        """컨텍스트 포함 코드 평가.

        Args:
            code: 평가할 코드
            context: 관련 컨텍스트 (호출 관계, 모듈 구조 등)

        Returns:
            평가 결과 딕셔너리
        """
        if not code.strip():
            return {"success": False, "error": "No code provided."}

        max_chars = 30000
        truncated = False
        total = code + context
        if len(total) > max_chars:
            # 코드 우선, 컨텍스트 줄이기
            context = context[: max(0, max_chars - len(code) - 500)]
            truncated = True

        try:
            response_text = self._call_gemini(
                EVALUATION_PROMPT.format(code=code, context=context or "N/A")
            )
            result = self._parse_evaluation(response_text)
        except Exception as e:
            return {"success": False, "error": f"Gemini API call failed: {e}"}

        if not result:
            return {
                "success": False,
                "error": "Failed to parse evaluation response.",
                "raw_response": response_text[:500] if response_text else "",
            }

        eval_id = str(uuid.uuid4())

        try:
            self._save_evaluation(
                file_path="context_eval",
                score=result["overall_score"],
                feedback=result.get("feedback", ""),
                criteria_scores=result.get("criteria", {}),
                eval_id=eval_id,
            )
        except Exception:
            pass

        return {
            "success": True,
            "file_path": "context_eval",
            "overall_score": result["overall_score"],
            "criteria": result.get("criteria", {}),
            "feedback": result.get("feedback", ""),
            "suggestions": result.get("suggestions", []),
            "eval_id": eval_id,
            "truncated": truncated,
        }

    def _call_gemini(self, prompt: str) -> str:
        """Gemini Flash API 호출.

        Args:
            prompt: 평가 프롬프트

        Returns:
            Gemini 응답 텍스트
        """
        response = _gemini_client.models.generate_content(
            model=self.model_name, contents=prompt
        )
        return response.text

    def _parse_evaluation(self, response: str) -> Optional[Dict]:
        """Gemini 응답을 파싱하여 평가 결과 딕셔너리로 변환.

        JSON 파싱 실패 시 regex fallback으로 점수를 추출한다.

        Args:
            response: Gemini 응답 텍스트

        Returns:
            파싱된 평가 결과 또는 None
        """
        if not response:
            return None

        # 1차: 직접 JSON 파싱
        try:
            # markdown 코드 블록 제거
            cleaned = response.strip()
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
            cleaned = cleaned.strip()

            data = json.loads(cleaned)
            return self._validate_evaluation(data)
        except (json.JSONDecodeError, ValueError):
            pass

        # 2차: 응답 내에서 JSON 블록 추출
        json_match = re.search(r"\{[\s\S]*\}", response)
        if json_match:
            try:
                data = json.loads(json_match.group())
                return self._validate_evaluation(data)
            except (json.JSONDecodeError, ValueError):
                pass

        # 3차: Regex fallback - 개별 점수 추출
        return self._regex_fallback(response)

    def _validate_evaluation(self, data: Dict) -> Optional[Dict]:
        """평가 결과의 유효성을 검증하고 정규화.

        Args:
            data: 파싱된 JSON 데이터

        Returns:
            검증된 평가 결과 또는 None
        """
        overall = data.get("overall_score")
        if overall is None:
            return None

        # 점수 범위 클램핑 (1-5)
        overall = max(1, min(5, int(overall)))

        criteria = data.get("criteria", {})
        normalized_criteria = {}
        for key in ("correctness", "security", "readability", "testability"):
            val = criteria.get(key)
            if val is not None:
                normalized_criteria[key] = max(1, min(5, int(val)))
            else:
                normalized_criteria[key] = overall  # fallback

        feedback = data.get("feedback", "")
        suggestions = data.get("suggestions", [])
        if isinstance(suggestions, str):
            suggestions = [suggestions]

        return {
            "overall_score": overall,
            "criteria": normalized_criteria,
            "feedback": str(feedback),
            "suggestions": [str(s) for s in suggestions],
        }

    def _regex_fallback(self, response: str) -> Optional[Dict]:
        """JSON 파싱 실패 시 regex로 점수 추출.

        Args:
            response: Gemini 응답 텍스트

        Returns:
            추출된 평가 결과 또는 None
        """
        # overall_score 추출
        overall_match = re.search(r'"overall_score"\s*:\s*(\d)', response)
        if not overall_match:
            # "Overall: 4/5" 같은 패턴도 시도
            overall_match = re.search(r"[Oo]verall[^:]*:\s*(\d)", response)
        if not overall_match:
            return None

        overall = max(1, min(5, int(overall_match.group(1))))

        criteria = {}
        for key in ("correctness", "security", "readability", "testability"):
            pattern = rf'"{key}"\s*:\s*(\d)'
            m = re.search(pattern, response, re.IGNORECASE)
            if m:
                criteria[key] = max(1, min(5, int(m.group(1))))
            else:
                criteria[key] = overall

        # feedback 추출
        feedback_match = re.search(r'"feedback"\s*:\s*"([^"]*)"', response)
        feedback = feedback_match.group(1) if feedback_match else ""

        # suggestions 추출
        suggestions = re.findall(r'"([^"]{10,})"', response)
        # feedback과 겹치는 것 제거
        suggestions = [s for s in suggestions if s != feedback and s not in (
            "overall_score", "criteria", "correctness", "security",
            "readability", "testability", "feedback", "suggestions"
        )]

        return {
            "overall_score": overall,
            "criteria": criteria,
            "feedback": feedback,
            "suggestions": suggestions[:5],
        }

    def _save_evaluation(
        self,
        file_path: str,
        score: int,
        feedback: str,
        criteria_scores: Dict,
        eval_id: str,
    ) -> None:
        """평가 이력을 Neo4j에 저장.

        Function 노드에 EVALUATED_BY 엣지를 연결한다.
        매칭되는 Function이 없으면 file_path 기반 Module에 연결을 시도한다.

        Args:
            file_path: 평가 대상 파일 경로
            score: 전체 점수 (1-5)
            feedback: 피드백 텍스트
            criteria_scores: 기준별 점수 딕셔너리
            eval_id: 평가 고유 ID
        """
        criteria_json = json.dumps(criteria_scores, ensure_ascii=False)

        # 파일명에서 함수명 추출 시도 (basename without ext)
        basename = os.path.basename(file_path)
        func_name = os.path.splitext(basename)[0] if basename else file_path

        query = """
        OPTIONAL MATCH (f:Function)
        WHERE f.name = $func_name OR f.file_path CONTAINS $file_path
        WITH f
        LIMIT 1
        WITH coalesce(f, null) AS target
        WHERE target IS NOT NULL
        MERGE (e:Evaluation {id: $eval_id})
        SET e.score = $score,
            e.feedback = $feedback,
            e.criteria = $criteria_json,
            e.evaluated_at = datetime(),
            e.model = 'gemini-3-flash-preview',
            e.file_path = $file_path
        MERGE (target)-[:EVALUATED_BY]->(e)
        RETURN target.name AS matched_name
        """

        # Function 매칭 안 되면 Module로 시도
        fallback_query = """
        MERGE (e:Evaluation {id: $eval_id})
        SET e.score = $score,
            e.feedback = $feedback,
            e.criteria = $criteria_json,
            e.evaluated_at = datetime(),
            e.model = 'gemini-3-flash-preview',
            e.file_path = $file_path
        RETURN e.id AS eval_id
        """

        try:
            with self.driver.session() as session:
                result = session.run(
                    query,
                    func_name=func_name,
                    file_path=file_path,
                    eval_id=eval_id,
                    score=score,
                    feedback=feedback,
                    criteria_json=criteria_json,
                )
                record = result.single()

                # 매칭되는 Function이 없으면 독립 Evaluation 노드만 생성
                if record is None or record.get("matched_name") is None:
                    session.run(
                        fallback_query,
                        eval_id=eval_id,
                        score=score,
                        feedback=feedback,
                        criteria_json=criteria_json,
                        file_path=file_path,
                    )
        except Exception as e:
            raise RuntimeError(f"Neo4j save failed: {e}") from e

    # ──────────────────────────────────────────────────────────────
    # Phase 6.7: Auto-feedback loop (Judge → Weight Learner)
    # ──────────────────────────────────────────────────────────────

    def _auto_feedback(self, eval_result: Dict, file_path: str):
        """평가 결과를 weight_learner에 자동 피드백.

        score 4+ -> success 피드백 (가중치 +0.2)
        score 2- -> failure 피드백 (가중치 -0.1)
        score 3  -> neutral (피드백 안 함)
        """
        score = eval_result.get("overall_score", 3)

        # 평가된 파일에서 관련 함수 이름 추출
        identifiers = self._extract_identifiers(file_path)
        if not identifiers:
            return

        from mcp_server.pipeline.weight_learner import NodeWeightLearner

        learner = NodeWeightLearner(self.driver)

        if score >= 4:
            learner.process_feedback("auto_judge", True, identifiers)
            logger.info(
                f"Auto-feedback: score={score}, SUCCESS for {len(identifiers)} nodes"
            )
        elif score <= 2:
            learner.process_feedback("auto_judge", False, identifiers)
            logger.info(
                f"Auto-feedback: score={score}, FAILURE for {len(identifiers)} nodes"
            )

        # 자동 승격: 5점 연속 3회
        if score == 5:
            self._check_auto_promote(identifiers)

    def _extract_identifiers(self, file_path: str) -> List[str]:
        """파일에서 관련 함수/클래스 이름 추출."""
        identifiers: List[str] = []
        try:
            with self.driver.session() as session:
                result = session.run(
                    """
                    MATCH (n:Function)
                    WHERE n.file_path CONTAINS $path OR n.module CONTAINS $path
                    RETURN n.name AS name
                    LIMIT 20
                    """,
                    path=os.path.basename(file_path),
                )
                identifiers = [r["name"] for r in result if r["name"]]
        except Exception:
            pass

        if not identifiers:
            # fallback: 파일명에서 추출
            basename = os.path.basename(file_path)
            name = os.path.splitext(basename)[0]
            identifiers = [name]

        return identifiers

    def _check_auto_promote(self, identifiers: List[str]):
        """5점 연속 3회인 노드를 자동 GLOBAL 승격."""
        try:
            with self.driver.session() as session:
                for name in identifiers:
                    # 최근 3회 평가 확인
                    result = session.run(
                        """
                        MATCH (f:Function {name: $name})-[:EVALUATED_BY]->(e:Evaluation)
                        WITH e ORDER BY e.evaluated_at DESC LIMIT 3
                        WITH collect(e.score) AS scores
                        WHERE size(scores) = 3 AND all(s IN scores WHERE s = 5)
                        RETURN true AS should_promote
                        """,
                        name=name,
                    ).single()

                    if result and result.get("should_promote"):
                        from mcp_server.pipeline.knowledge_transfer import (
                            KnowledgeTransfer,
                        )

                        transfer = KnowledgeTransfer(self.driver)
                        transfer.promote_pattern(name)
                        logger.info(
                            f"Auto-promoted '{name}' to GLOBAL (3x perfect score)"
                        )
        except Exception as e:
            logger.debug(f"Auto-promote check failed: {e}")

    def get_evaluation_history(self, limit: int = 10) -> Dict:
        """최근 평가 이력 조회."""
        try:
            with self.driver.session() as session:
                result = session.run(
                    """
                    MATCH (e:Evaluation)
                    OPTIONAL MATCH (f)-[:EVALUATED_BY]->(e)
                    RETURN e.id AS eval_id, e.score AS score,
                           e.feedback AS feedback, e.file_path AS file_path,
                           e.evaluated_at AS evaluated_at,
                           f.name AS function_name
                    ORDER BY e.evaluated_at DESC
                    LIMIT $limit
                    """,
                    limit=limit,
                )
                evals = [dict(r) for r in result]

                # 통계
                scores = [e["score"] for e in evals if e.get("score")]
                avg_score = sum(scores) / len(scores) if scores else 0

                return {
                    "success": True,
                    "evaluations": evals,
                    "total": len(evals),
                    "average_score": round(avg_score, 2),
                }
        except Exception as e:
            return {"success": False, "error": str(e)}
