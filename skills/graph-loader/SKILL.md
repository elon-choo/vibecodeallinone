---
name: graph-loader
description: "JSON-to-Neo4j graph loader. Loads knowledge_packet.json into Neo4j as nodes and edges. Use when loading project patterns, rules, or code knowledge into the graph database."
license: MIT
allowed-tools: Read Glob Grep Bash
---

# Graph Loader Skill

## Description
JSON 데이터를 Neo4j 데이터베이스에 노드와 엣지로 적재합니다.

## When to Use
- `knowledge_packet.json` 파일을 Neo4j에 적재할 때
- 프로젝트 패턴, 규칙을 그래프 DB에 저장할 때
- 'graph load', 'neo4j 적재', '그래프 로드', '지식 적재' 요청 시 자동 발동

## Prerequisites
- Neo4j 데이터베이스 실행 중
- `.env` 파일에 Neo4j 연결 정보 설정
- Python `neo4j` 패키지 설치

## Environment Variables (.env)
```bash
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
```

## Usage

### 1. CLI 직접 실행 (WSL/Windows)
```bash
# macOS / Linux
python3 ~/.claude/skills/graph-loader/loader.py /path/to/knowledge_packet.json
```

### 2. Claude Code 내부에서 실행
```bash
# 현재 디렉토리의 knowledge_packet.json 사용
python3 ~/.claude/skills/graph-loader/loader.py ./knowledge_packet.json
```

## Input Format (knowledge_packet.json)
```json
{
  "repo": "project-name",
  "patterns": [
    {
      "name": "singleton",
      "rules": ["전역 인스턴스 하나만 생성", "private 생성자 사용"]
    },
    {
      "name": "factory",
      "rules": ["객체 생성 로직 캡슐화"]
    }
  ]
}
```

## Output
- 적재 성공 메시지
- 생성된 노드 개수 (Project, Pattern, Rule)
- 생성된 관계 개수 (IMPLEMENTS, HAS_RULE)

## Neo4j Schema
```cypher
(:Project {name: string})
(:Pattern {name: string})
(:Rule {desc: string})

(:Project)-[:IMPLEMENTS]->(:Pattern)
(:Pattern)-[:HAS_RULE]->(:Rule)
```

## Troubleshooting

### 연결 실패
```bash
# Neo4j 상태 확인 (WSL)
sudo systemctl status neo4j

# Docker로 실행 중인 경우
docker ps | grep neo4j
```

### 인증 오류
`.env` 파일의 `NEO4J_USER`와 `NEO4J_PASSWORD` 확인

### 패키지 미설치
```bash
pip install neo4j python-dotenv
```
