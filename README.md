---
title: CodeReviewEnv
emoji: 🔍
colorFrom: blue
colorTo: purple
sdk: docker
pinned: false
tags:
  - openenv
  - code-review
  - reinforcement-learning
  - agent-environment
  - security
---

# CodeReviewEnv

An OpenEnv-compatible environment where AI agents review Python code,
identify bugs, and submit secure fixes — a real task done by engineers every day.

## Project structure

```
code-review-env/
├── __init__.py                      ← exports Action, Observation, Client
├── client.py                        ← typed EnvClient (agents use this)
├── models.py                        ← Pydantic models (Action, Observation, Reward)
├── inference.py                     ← baseline inference script
├── pyproject.toml                   ← dependencies
├── openenv.yaml                     ← OpenEnv manifest
├── README.md
└── server/
    ├── __init__.py
    ├── app.py                       ← FastAPI server
    ├── code_review_environment.py   ← Environment logic
    ├── tasks.py                     ← 3 task definitions
    ├── grader.py                    ← deterministic graders
    └── Dockerfile
```

## Tasks

| Task | Difficulty | Bug type | Max score |
|------|-----------|----------|-----------|
| `task_easy` | Easy | ZeroDivisionError on empty list | 1.0 |
| `task_medium` | Medium | 2 bugs: off-by-one + float division | 1.0 |
| `task_hard` | Hard | 3 security bugs: SQL injection, timing attack, plaintext password | 1.0 |

## Observation space

| Field | Type | Description |
|-------|------|-------------|
| `task_id` | string | Active task identifier |
| `task_description` | string | Full instructions for the agent |
| `code_files` | array | Files to review (filename, content, language) |
| `current_feedback` | array | History of actions this episode |
| `tests_passed` | int | Tests passed |
| `tests_total` | int | Total tests for task |
| `step_count` | int | Current step |
| `done` | bool | Episode finished? |

## Action space

| Field | Type | Required for | Description |
|-------|------|-------------|-------------|
| `action_type` | string | all | `"comment"`, `"fix"`, or `"submit"` |
| `line_number` | int | comment | Line where bug was found |
| `comment_text` | string | comment | Bug explanation |
| `filename` | string | fix | File being corrected |
| `fixed_content` | string | fix | Entire corrected file |
| `final_summary` | string | submit | Summary of all changes |

## Reward function

| Signal | Value |
|--------|-------|
| Comment with line number | +0.08 |
| Substantive comment text | +0.07 |
| Fix submitted | +0.10 |
| Empty comment spam | −0.05 |
| Final: bug identified | +0.10–0.20 |
| Final: correct fix | +0.20–0.30 |
| Final: valid syntax | +0.15 |
| Final: security fix (AST verified) | +0.25 |
| Final: vulnerability still present | −0.20 to −0.30 |

## Baseline scores

Scores produced by running `inference.py` with `Qwen/Qwen2.5-72B-Instruct`
via the HuggingFace router.

| Task | Difficulty | Score |
|------|-----------|-------|
| task_easy | Easy | 1.000 |
| task_medium | Medium | 1.000 |
| task_hard | Hard | 0.700 |
| **Average** | | **0.900** |

## Setup

```bash
# Local dev
pip install -e ".[server,inference]"
uvicorn server.app:app --host 0.0.0.0 --port 7860

# Docker
docker build -f server/Dockerfile -t code-review-env .
docker run -p 7860:7860 code-review-env

# Run inference
HF_TOKEN=your_token \
API_BASE_URL=https://router.huggingface.co/v1 \
MODEL_NAME=Qwen/Qwen2.5-72B-Instruct \
python inference.py
```

## API

```bash
# Start episode
curl -X POST http://localhost:7860/reset \
     -H "Content-Type: application/json" -d '{"task_id": "task_easy"}'

# Take action
curl -X POST http://localhost:7860/step \
     -H "Content-Type: application/json" \
     -d '{"action_type": "comment", "line_number": 5, "comment_text": "ZeroDivisionError when list is empty"}'

# Get state
curl http://localhost:7860/state
```