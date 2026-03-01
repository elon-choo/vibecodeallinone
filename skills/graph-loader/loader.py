#!/usr/bin/env python3
"""
Graph Loader v3 - Neo4j Knowledge Packet Loader with Vector Embeddings
JSON 데이터를 Neo4j 데이터베이스에 노드와 엣지로 적재합니다.
벡터 임베딩을 지원하여 의미 기반 검색이 가능합니다.

Usage:
    python loader.py <knowledge_packet.json>
    python loader.py <knowledge_packet.json> --embed  # 임베딩 포함 적재
    python loader.py --create-index  # 벡터 인덱스 생성
    python loader.py  # 현재 디렉토리의 knowledge_packet.json 사용

Cross-platform: WSL Ubuntu & Windows PowerShell 모두 지원
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List

# Optional imports with graceful fallback
try:
    from neo4j import GraphDatabase
    HAS_NEO4J = True
except ImportError:
    HAS_NEO4J = False

try:
    from dotenv import load_dotenv
    HAS_DOTENV = True
except ImportError:
    HAS_DOTENV = False

try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False


def find_env_file() -> Optional[Path]:
    """
    .env 파일을 찾습니다.
    검색 순서: 현재 디렉토리 -> 스킬 디렉토리 -> 홈 디렉토리 -> WSL Windows 경로
    """
    # WSL 환경에서 Windows 경로 지원
    wsl_windows_home = Path(os.getenv('HOME', os.path.expanduser('~')))

    search_paths = [
        Path.cwd() / ".env",
        Path(__file__).parent / ".env",
        Path.home() / ".claude" / "skills" / ".env.local",
        Path.home() / ".claude" / ".env",
        Path.home() / ".env",
        # WSL Windows 경로
        wsl_windows_home / ".claude" / "skills" / ".env.local",
        wsl_windows_home / ".claude" / ".env",
    ]

    for env_path in search_paths:
        if env_path.exists():
            return env_path
    return None


def load_environment() -> Dict[str, str]:
    """환경 변수를 로드합니다."""
    env_vars = {}

    # .env 파일 로드 시도
    env_file = find_env_file()
    if env_file and HAS_DOTENV:
        load_dotenv(env_file)
        print(f"[INFO] .env 로드됨: {env_file}")

    # 환경 변수 읽기 (NEO4J_USER, NEO4J_USERNAME 둘 다 지원)
    env_vars['uri'] = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
    env_vars['user'] = os.getenv('NEO4J_USER') or os.getenv('NEO4J_USERNAME', 'neo4j')
    env_vars['password'] = os.getenv('NEO4J_PASSWORD', '')

    return env_vars


def load_knowledge_packet(file_path: Path) -> Dict[str, Any]:
    """knowledge_packet.json 파일을 로드합니다."""
    if not file_path.exists():
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_path}")

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    return data


class Neo4jLoader:
    """Neo4j 데이터 적재기 v3 - Pattern + Error/Solution + Vector Embeddings 지원"""

    def __init__(self, uri: str, user: str, password: str, enable_embeddings: bool = False):
        if not HAS_NEO4J:
            raise ImportError("neo4j 패키지가 설치되지 않았습니다. pip install neo4j")

        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.enable_embeddings = enable_embeddings
        self.openai_client = None

        # OpenAI 클라이언트 초기화 (임베딩 활성화 시)
        if enable_embeddings:
            if not HAS_OPENAI:
                print("[WARN] openai 패키지가 없습니다. pip install openai")
                self.enable_embeddings = False
            else:
                api_key = os.getenv('OPENAI_API_KEY')
                if api_key:
                    self.openai_client = OpenAI(api_key=api_key)
                    print("[OK] OpenAI 임베딩 활성화됨")
                else:
                    print("[WARN] OPENAI_API_KEY가 없습니다. 임베딩 비활성화")
                    self.enable_embeddings = False

        self._stats = {
            'projects': 0,
            'patterns': 0,
            'rules': 0,
            'errors': 0,
            'solutions': 0,
            'embeddings': 0,
            'implements_rels': 0,
            'has_rule_rels': 0,
            'solved_by_rels': 0
        }

    def close(self):
        """드라이버 연결을 닫습니다."""
        if self.driver:
            self.driver.close()

    def verify_connection(self) -> bool:
        """연결을 확인합니다."""
        try:
            with self.driver.session() as session:
                session.run("RETURN 1")
            return True
        except Exception as e:
            print(f"[ERROR] Neo4j 연결 실패: {e}")
            return False

    def create_embedding(self, text: str) -> Optional[List[float]]:
        """OpenAI API로 텍스트 임베딩 생성"""
        if not self.openai_client:
            return None

        try:
            response = self.openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=text[:8000]  # 최대 토큰 제한
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"[WARN] 임베딩 생성 실패: {e}")
            return None

    def create_vector_index(self) -> bool:
        """Neo4j 벡터 인덱스 생성"""
        try:
            with self.driver.session() as session:
                # 기존 인덱스 확인
                result = session.run("""
                    SHOW INDEXES
                    YIELD name, type
                    WHERE type = 'VECTOR' AND name = 'error_embeddings'
                    RETURN count(*) AS count
                """)
                record = result.single()
                if record and record['count'] > 0:
                    print("[INFO] 벡터 인덱스가 이미 존재합니다")
                    return True

                # 벡터 인덱스 생성
                session.run("""
                    CREATE VECTOR INDEX error_embeddings IF NOT EXISTS
                    FOR (e:Error) ON e.embedding
                    OPTIONS {
                        indexConfig: {
                            `vector.dimensions`: 1536,
                            `vector.similarity_function`: 'cosine'
                        }
                    }
                """)
                print("[OK] 벡터 인덱스 생성됨: error_embeddings")
                return True

        except Exception as e:
            print(f"[ERROR] 인덱스 생성 실패: {e}")
            return False

    def load_data(self, data: Dict[str, Any]) -> Dict[str, int]:
        """데이터를 Neo4j에 적재합니다. (Pattern 및 Error 지원)"""

        # 데이터 타입 감지
        data_type = data.get('type', 'knowledge_packet')

        if data_type == 'error_knowledge':
            return self._load_error_data(data)
        else:
            return self._load_pattern_data(data)

    def _load_pattern_data(self, data: Dict[str, Any]) -> Dict[str, int]:
        """Pattern 데이터 적재 (기존 형식)"""
        with self.driver.session() as session:
            # 1. Project 노드 생성
            repo_name = data.get('repo', 'unknown')
            session.execute_write(self._create_project, repo_name)
            self._stats['projects'] = 1
            print(f"[OK] Project 노드 생성: {repo_name}")

            # 2. Pattern 및 Rule 노드 생성
            patterns = data.get('patterns', [])
            for pattern in patterns:
                # 호환성: 'name' 또는 'pattern' 키 지원
                pattern_name = pattern.get('name') or pattern.get('pattern', 'unnamed')
                # 호환성: 'rules' 배열 또는 단일 'rule' 지원
                rules = pattern.get('rules', [])
                if not rules and pattern.get('rule'):
                    rules = [pattern.get('rule')]

                # Pattern 노드 생성 및 Project와 연결
                session.execute_write(
                    self._create_pattern_with_project,
                    repo_name,
                    pattern_name
                )
                self._stats['patterns'] += 1
                self._stats['implements_rels'] += 1

                # Rule 노드들 생성 및 Pattern과 연결
                for rule_desc in rules:
                    session.execute_write(
                        self._create_rule_with_pattern,
                        pattern_name,
                        rule_desc
                    )
                    self._stats['rules'] += 1
                    self._stats['has_rule_rels'] += 1

                print(f"  [OK] Pattern '{pattern_name}' + {len(rules)}개 Rule 적재됨")

        return self._stats

    def _load_error_data(self, data: Dict[str, Any]) -> Dict[str, int]:
        """Error 데이터 적재 (새 형식) - 임베딩 지원"""
        with self.driver.session() as session:
            errors = data.get('errors', [])

            for error in errors:
                error_id = error.get('id', 'unknown')
                message = error.get('message', '')
                error_type = error.get('error_type', 'Unknown')
                language = error.get('language', 'Unknown')
                framework = error.get('framework', 'Unknown')
                stack_trace = error.get('stack_trace', '')
                source_url = error.get('source_url', '')

                # 임베딩 생성 (활성화된 경우)
                embedding = None
                if self.enable_embeddings:
                    # 임베딩용 텍스트 생성
                    embed_text = f"{message} {error_type} {language} {framework}"
                    embedding = self.create_embedding(embed_text)
                    if embedding:
                        self._stats['embeddings'] += 1

                # Error 노드 생성 (임베딩 포함)
                session.execute_write(
                    self._create_error_with_embedding,
                    error_id, message, error_type, language, framework, stack_trace, source_url, embedding
                )
                self._stats['errors'] += 1

                # Solution 노드들 생성 및 Error와 연결
                solutions = error.get('solutions', [])
                for solution in solutions:
                    solution_desc = solution.get('description', '')
                    solution_code = solution.get('code', '')
                    confidence = solution.get('confidence', 0.5)

                    if solution_desc:
                        session.execute_write(
                            self._create_solution_with_error,
                            error_id, solution_desc, solution_code, confidence
                        )
                        self._stats['solutions'] += 1
                        self._stats['solved_by_rels'] += 1

                embed_status = "+" if embedding else "-"
                print(f"  [OK] Error '{error_type}' + {len(solutions)}개 Solution 적재됨 [embed:{embed_status}]")

        return self._stats

    @staticmethod
    def _create_error(tx, error_id: str, message: str, error_type: str,
                      language: str, framework: str, stack_trace: str, source_url: str):
        """Error 노드를 생성합니다."""
        query = """
        MERGE (e:Error {id: $error_id})
        SET e.message = $message,
            e.type = $error_type,
            e.language = $language,
            e.framework = $framework,
            e.stack_trace = $stack_trace,
            e.source_url = $source_url
        RETURN e
        """
        tx.run(query, error_id=error_id, message=message, error_type=error_type,
               language=language, framework=framework, stack_trace=stack_trace, source_url=source_url)

    @staticmethod
    def _create_error_with_embedding(tx, error_id: str, message: str, error_type: str,
                                      language: str, framework: str, stack_trace: str,
                                      source_url: str, embedding: Optional[List[float]]):
        """Error 노드를 임베딩과 함께 생성합니다."""
        if embedding:
            query = """
            MERGE (e:Error {id: $error_id})
            SET e.message = $message,
                e.type = $error_type,
                e.language = $language,
                e.framework = $framework,
                e.stack_trace = $stack_trace,
                e.source_url = $source_url,
                e.embedding = $embedding
            RETURN e
            """
            tx.run(query, error_id=error_id, message=message, error_type=error_type,
                   language=language, framework=framework, stack_trace=stack_trace,
                   source_url=source_url, embedding=embedding)
        else:
            query = """
            MERGE (e:Error {id: $error_id})
            SET e.message = $message,
                e.type = $error_type,
                e.language = $language,
                e.framework = $framework,
                e.stack_trace = $stack_trace,
                e.source_url = $source_url
            RETURN e
            """
            tx.run(query, error_id=error_id, message=message, error_type=error_type,
                   language=language, framework=framework, stack_trace=stack_trace, source_url=source_url)

    @staticmethod
    def _create_solution_with_error(tx, error_id: str, description: str, code: str, confidence: float):
        """Solution 노드를 생성하고 Error와 연결합니다."""
        query = """
        MATCH (e:Error {id: $error_id})
        MERGE (s:Solution {description: $description})
        SET s.code = $code
        MERGE (e)-[:SOLVED_BY {confidence: $confidence}]->(s)
        RETURN s
        """
        tx.run(query, error_id=error_id, description=description, code=code, confidence=confidence)

    @staticmethod
    def _create_project(tx, repo_name: str):
        """Project 노드를 생성합니다."""
        query = """
        MERGE (p:Project {name: $repo})
        RETURN p
        """
        tx.run(query, repo=repo_name)

    @staticmethod
    def _create_pattern_with_project(tx, repo_name: str, pattern_name: str):
        """Pattern 노드를 생성하고 Project와 연결합니다."""
        query = """
        MERGE (p:Project {name: $repo})
        MERGE (pt:Pattern {name: $pattern})
        MERGE (p)-[:IMPLEMENTS]->(pt)
        RETURN pt
        """
        tx.run(query, repo=repo_name, pattern=pattern_name)

    @staticmethod
    def _create_rule_with_pattern(tx, pattern_name: str, rule_desc: str):
        """Rule 노드를 생성하고 Pattern과 연결합니다."""
        query = """
        MERGE (pt:Pattern {name: $pattern})
        MERGE (r:Rule {desc: $rule})
        MERGE (pt)-[:HAS_RULE]->(r)
        RETURN r
        """
        tx.run(query, pattern=pattern_name, rule=rule_desc)


def print_summary(stats: Dict[str, int]):
    """적재 결과 요약을 출력합니다."""
    print("\n" + "=" * 50)
    print("        Graph Loader v3 적재 완료")
    print("=" * 50)
    print(f"  생성된 노드:")
    if stats.get('projects', 0) > 0:
        print(f"    - Project:   {stats['projects']}개")
    if stats.get('patterns', 0) > 0:
        print(f"    - Pattern:   {stats['patterns']}개")
    if stats.get('rules', 0) > 0:
        print(f"    - Rule:      {stats['rules']}개")
    if stats.get('errors', 0) > 0:
        print(f"    - Error:     {stats['errors']}개")
    if stats.get('solutions', 0) > 0:
        print(f"    - Solution:  {stats['solutions']}개")
    print(f"  생성된 관계:")
    if stats.get('implements_rels', 0) > 0:
        print(f"    - IMPLEMENTS: {stats['implements_rels']}개")
    if stats.get('has_rule_rels', 0) > 0:
        print(f"    - HAS_RULE:   {stats['has_rule_rels']}개")
    if stats.get('solved_by_rels', 0) > 0:
        print(f"    - SOLVED_BY:  {stats['solved_by_rels']}개")
    if stats.get('embeddings', 0) > 0:
        print(f"  벡터 임베딩:")
        print(f"    - Embeddings: {stats['embeddings']}개")
    print("=" * 50)


def main():
    """메인 함수"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Graph Loader v3 - Neo4j Knowledge Packet Loader with Vector Embeddings'
    )
    parser.add_argument('input_file', nargs='?', default='knowledge_packet.json',
                        help='입력 JSON 파일 경로')
    parser.add_argument('--embed', action='store_true',
                        help='OpenAI 임베딩 생성 및 저장')
    parser.add_argument('--create-index', action='store_true',
                        help='Neo4j 벡터 인덱스 생성 (데이터 적재 없이)')

    args = parser.parse_args()

    print("\n[Graph Loader v3] Neo4j Knowledge Packet Loader")
    print("-" * 50)

    # 2. 필수 패키지 확인
    if not HAS_NEO4J:
        print("[ERROR] neo4j 패키지가 필요합니다.")
        print("        설치: pip install neo4j python-dotenv openai")
        sys.exit(1)

    # 3. 환경 변수 로드
    env = load_environment()
    print(f"[INFO] Neo4j URI: {env['uri']}")
    print(f"[INFO] Neo4j User: {env['user']}")

    if not env['password']:
        print("[WARN] NEO4J_PASSWORD가 설정되지 않았습니다.")

    # 벡터 인덱스만 생성하는 경우
    if args.create_index:
        loader = None
        try:
            loader = Neo4jLoader(env['uri'], env['user'], env['password'])
            if not loader.verify_connection():
                print("[ERROR] Neo4j 연결을 확인해주세요.")
                sys.exit(1)

            print("[OK] Neo4j 연결 성공")
            success = loader.create_vector_index()
            if success:
                print("\n[SUCCESS] 벡터 인덱스가 준비되었습니다!")
            else:
                sys.exit(1)
        finally:
            if loader:
                loader.close()
        return

    # 1. 입력 파일 경로 결정
    input_file = Path(args.input_file).resolve()
    print(f"[INFO] 입력 파일: {input_file}")

    if args.embed:
        print("[INFO] 임베딩 모드 활성화")

    # 4. JSON 파일 로드
    try:
        data = load_knowledge_packet(input_file)
        print(f"[OK] JSON 파일 로드 완료")
    except FileNotFoundError as e:
        print(f"[ERROR] {e}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"[ERROR] JSON 파싱 오류: {e}")
        sys.exit(1)

    # 5. Neo4j 연결 및 데이터 적재
    loader = None
    try:
        loader = Neo4jLoader(env['uri'], env['user'], env['password'], enable_embeddings=args.embed)

        if not loader.verify_connection():
            print("[ERROR] Neo4j 연결을 확인해주세요.")
            sys.exit(1)

        print("[OK] Neo4j 연결 성공")

        stats = loader.load_data(data)
        print_summary(stats)

    except Exception as e:
        print(f"[ERROR] 적재 실패: {e}")
        sys.exit(1)
    finally:
        if loader:
            loader.close()

    print("\n[SUCCESS] 적재가 완료되었습니다!")


if __name__ == "__main__":
    main()
