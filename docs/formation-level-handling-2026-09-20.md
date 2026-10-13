# Formation level handling — 20 September 2026

Verdict: `FORMATION_LEVEL_HANDLING_COMPLETE` for the requested behavior. The full
repository validation has unrelated failures documented below; this is not a claim
that every backend test or the repository-wide lint check is green.

## Implementation

FILES_CHANGED=

- `backend/app/learning/level_resolution.py` (new shared deterministic helper)
- `backend/app/formation/agent.py`
- `backend/app/orientation/agent.py`
- `backend/app/graph/workflow_context.py`
- `backend/app/graph/supervisor.py`
- `backend/app/quiz/agent.py` (explicit assessment starts the existing diagnostic bank,
  including when a level is already stored; scoring and questions are unchanged)
- `backend/tests/unit/test_learning_level_resolution.py` (new regressions)
- `backend/tests/unit/test_j7_formation_agent.py`
- `backend/tests/unit/test_j7_orientation_agent.py`
- `backend/tests/integration/test_j7_orientation_pipeline.py`
- `backend/tests/integration/test_j7_multilingual_e2e.py`
- `backend/scripts/check_formation_levels_live.py` (reproducible runtime checks)
- This report; generated evidence in `backend/reports/formation-level-live.json`
  and `backend/reports/formation-level-backend-tests.txt`.

LEVEL_EXTRACTOR= `extract_level` and `resolve_level` use the current normalized
message, the existing accent/case normalization utility, whole-term matching and
affirmative first-person phrasing. Bare levels are accepted while a level question
is pending. Statements about market levels or course difficulty do not establish
a personal level. Ambiguous conflicting self-reports are not selected. No LLM call
is added. The existing profile service persists manual selections.

SUPPORTED_LEVEL_VARIANTS=

| Level | Variants (accents and case normalized) |
|---|---|
| beginner | débutant, débutante, beginner, مبتدئ, مبتدئة, moubtadi, mobtadi, mobtadi2 |
| intermediate | intermédiaire, intermediate, متوسط, متوسطة, متوسط المستوى, moutawassit, motawassit |
| advanced | avancé/avance, avancée, advanced, متقدم, متقدمة, mota9adim, motaqadim, mouta9addem |

CLARIFICATION_FLOW= Missing profile level asks one localized question in FR, EN,
AR, ARY Latin or ARY Arabic. The existing checkpointed workflow stores
`workflow_step=learning_level`, the owning agent and expected choices. A matching
reply resumes that workflow without another Supervisor call, saves `manual` and
starts the corresponding existing module path. Unrelated messages still go to the
Supervisor. Existing known levels are reused. An explicit replacement level starts
the matching path instead of retaining a mismatched session.

DIAGNOSTIC_FLOW_PRESERVED= Explicit assessment requests use the existing six-question
diagnostic, even with a stored level. Legacy diagnostic tests now explicitly request
assessment. Quiz content, scoring and profile persistence are unchanged.

SUPERVISOR_RULE_UPDATED= The existing Supervisor instruction distinguishes explicit
courses/modules/e-learning from open-ended learning guidance. Level extraction stays
in the shared learning helper. Both requested routing examples passed with the live
provider.

RAG, Azure composer, Voice, learning module content and persistence schemas were not
modified by this task.

## Validation

TESTS_PASSED= 317 targeted tests passed across level extraction, formation content
and agents, orientation, quiz, learning profiles, persistent profiles, Supervisor,
multilingual integration and conversation continuity.

Ruff passes for all files changed by this task. Python compilation passes for
`app`, `tests` and the new live-check script. Repository-wide Ruff reports two
existing E501 lines in `tests/unit/test_f2d_contextual_retrieval.py:125` and `:413`;
that RAG test file was left unchanged.

The broad backend run covers `tests/unit tests/integration tests/api`: **1739 passed,
4 failed** (76.18 seconds). Four unrelated
failures remain in unchanged test/code paths:

- Two `test_performance_finalization.py` warm-up tests provide an embedding-only
  fake, whereas the existing warm-up calls `service._query`.
- Two Darija cases in `test_general_bourse_external_research.py` supply a localization
  fake without the `provider` attribute read by existing chat logging.

See `backend/reports/formation-level-backend-tests.txt` for the complete run result.

## Live checks

All six HTTP requests returned 200 with `status=ok` using real providers. Evidence:
`backend/reports/formation-level-live.json`, thread prefix `level-check-060b29e634`.

LIVE_TEST_A= PASS: `formation_elearning`; “Parcours débutant — Module 1/8 : Rôle
d’une Bourse”, without a diagnostic or level question.

LIVE_TEST_B= PASS: `formation_elearning`; asks “Quel est votre niveau actuel en
Bourse : débutant, intermédiaire ou avancé ?”. Same-thread “intermédiaire” immediately
returns “Parcours intermédiaire — Module 1/8 : Organisation du marché”.

LIVE_TEST_C= PASS: `quiz`; existing diagnostic “Question 1/6” with four choices.

Routing checks: “Je veux suivre des modules de formation e-learning.” returns
`formation_elearning`; “Je ne sais pas par où commencer mon apprentissage.” returns
`orientation`.

Read-only PostgreSQL verification confirmed:

| Thread suffix | learning_level | level_source | current_learning_path | diagnostic_completed |
|---|---|---|---|---|
| -a | beginner | manual | beginner_financial_learning | false |
| -b | intermediate | manual | intermediate_financial_learning | false |

Backend restarted with the final implementation; application remains available at
http://localhost:5173 with the API at http://127.0.0.1:8080.
