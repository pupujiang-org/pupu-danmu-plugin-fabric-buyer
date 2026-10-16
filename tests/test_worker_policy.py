"""Standalone regressions for the independent fabric Worker rules."""

from __future__ import annotations

import ast
import json
import unittest
import zipfile
from io import BytesIO
from pathlib import Path

from worker.fabric_buyer.participation import BUYER_CLOTH_PARTICIPATION_INTERPRETER
from worker.fabric_buyer.policy import FabricBuyerPolicy
from worker.fabric_buyer.topics import priority_for
from worker.fabric_buyer.topics import topics_in
from worker.fabric_buyer.types import BootstrapContext
from worker.fabric_buyer.types import ContextPhase

from scripts import package_plugins

ROOT = Path(__file__).resolve().parents[1]
GOLD_SET_PATH = ROOT / "tests" / "fixtures" / "buyer_cloth_policy_gold_set.json"


def _rolling_projection(policy: FabricBuyerPolicy) -> dict[str, object]:
    rolling = policy.rolling_content_policy
    return {
        "tags": list(rolling.tags),
        "quotas": [
            {
                "tag": quota.tag,
                "window_size": quota.window_size,
                "max_count": quota.max_count,
            }
            for quota in rolling.quotas
        ],
    }


class FabricWorkerPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.gold = json.loads(GOLD_SET_PATH.read_text(encoding="utf-8"))
        cls.policy = FabricBuyerPolicy()

    def test_candidate_corpus_and_objective_claims_match_legacy_gold_set(self) -> None:
        cases = [
            *self.gold["candidate_cases"],
            *self.gold["legacy_candidate_corpus"],
        ]
        self.assertEqual(
            len(self.gold["legacy_candidate_corpus"]),
            self.gold["legacy_candidate_corpus_count"],
        )
        for case in cases:
            with self.subTest(case=case["id"]):
                decision = self.policy.evaluate(case["candidate"])
                self.assertEqual(decision.allowed, case["legacy_allowed"])
                self.assertEqual(decision.reason or "", case["legacy_reason"])

        self.assertEqual(len(self.gold["objective_claim_cases"]), 16)
        for case in self.gold["objective_claim_cases"]:
            with self.subTest(claim_case=case["id"]):
                claims = self.policy.objective_fact_claims(case["candidate"])
                self.assertEqual(
                    [claim.predicate for claim in claims],
                    case["legacy_claim_predicates"],
                )

    def test_context_and_rolling_quota_match_legacy_gold_set(self) -> None:
        for case in [self.gold["context_case"], *self.gold["context_cases"]]:
            with self.subTest(context=case["id"]):
                decision = self.policy.evaluate_with_context(
                    case["candidate"],
                    recent_chat=tuple(case["recent_chat"]),
                    user_topic=case["user_topic"],
                )
                self.assertEqual(decision.allowed, case["legacy_allowed"])
                self.assertEqual(decision.reason or "", case["legacy_reason"])

        self.assertEqual(
            _rolling_projection(self.policy), self.gold["legacy_rolling_policy"]
        )
        for case in self.gold["rolling_quota_cases"]:
            candidate = self.policy.evaluate_with_context(
                case["candidate"], recent_chat=(), user_topic=""
            )
            history = tuple(
                self.policy.evaluate_with_context(
                    text, recent_chat=(), user_topic=""
                ).tags
                for text in case["submitted_candidates"]
            )
            decision = self.policy.rolling_content_policy.evaluate(
                candidate_tags=candidate.tags,
                submitted_history=history,
            )
            with self.subTest(quota=case.get("id", case["candidate"])):
                self.assertEqual(decision.allowed, case["legacy_allowed"])

    def test_persona_topic_prompt_and_participation_match_legacy_gold_set(self) -> None:
        profiles = [
            {
                "id": item.archetype_id,
                "display_name": item.display_name,
                "description": item.description,
                "information_needs": list(item.information_needs),
                "style_tendencies": list(item.style_tendencies),
                "topic_interests": [
                    {
                        "topic_id": interest.topic_id,
                        "relevance": interest.relevance,
                        "related_topic_ids": list(interest.related_topic_ids),
                    }
                    for interest in item.topic_interests
                ],
            }
            for item in self.policy.viewer_archetypes
        ]
        self.assertEqual(profiles, self.gold["legacy_persona_profiles"])

        for case in self.gold["topic_tag_cases"]:
            with self.subTest(topic_tags=case["text"]):
                self.assertEqual(
                    list(self.policy.viewer_topic_tags(case["text"])),
                    case["legacy_tags"],
                )
        for case in self.gold["usage_group_cases"]:
            with self.subTest(usage_group=case["text"]):
                self.assertEqual(
                    self.policy.usage_group_for(case["text"]), case["legacy_group"]
                )
        for case in self.gold["usage_priority_cases"]:
            with self.subTest(usage_priority=case.get("id", case["candidate"])):
                self.assertIn(
                    case["topic"],
                    {topic.name for topic in topics_in(case["candidate"])},
                )
                priority = priority_for(case["candidate"])
                self.assertIsNotNone(priority)
                self.assertEqual(priority.value, case["priority"])

        bootstrap = BootstrapContext(streamer_name="主播A", platform_id="douyin")
        for case in self.gold["prompt_projection_cases"]:
            projection = self.policy.project_prompt(
                phase=ContextPhase(case["phase"]), bootstrap=bootstrap
            )
            actual = {
                "revision": projection.revision,
                "preferred_intents": list(projection.preferred_intents),
                "forbidden_dimensions": list(projection.forbidden_dimensions),
                "phase_notes": list(projection.phase_notes),
                "hard_constraints": list(projection.hard_constraints),
            }
            with self.subTest(prompt=case["phase"]):
                self.assertEqual(actual, case["legacy_projection"])

        interpreter = BUYER_CLOTH_PARTICIPATION_INTERPRETER
        for surface, cases in self.gold["legacy_participation_cases"].items():
            for case in cases:
                with self.subTest(surface=surface, case=case["id"]):
                    if surface == "act_resolution":
                        actual = interpreter.resolve_participation_act(
                            case["text"], case["declared"]
                        )
                    elif surface == "grounding":
                        actual = interpreter.requires_external_grounding(
                            case["text"], case["act"], initiative=case["initiative"]
                        )
                    elif surface == "answer_topic_tags":
                        actual = sorted(
                            interpreter.answer_topic_tags_for_question(
                                case["text"],
                                topic_tags=frozenset(case["topic_tags"]),
                                candidate_tags=tuple(case["candidate_tags"]),
                            )
                        )
                    elif surface == "answer_evidence":
                        actual = interpreter.has_answer_evidence(
                            case["text"], topic_tags=frozenset(case["topic_tags"])
                        )
                    else:
                        actual = interpreter.has_explicit_topic_shift(case["text"])
                    expected = case.get("expected_tags", case.get("expected"))
                    self.assertEqual(actual, expected)

        for case in self.gold["data_only_participation_gaps"]:
            surface = case["surface"]
            with self.subTest(participation_gap=case["id"]):
                if surface == "resolve_participation_act":
                    actual = interpreter.resolve_participation_act(
                        case["text"], case["declared"]
                    )
                elif surface == "has_answer_evidence":
                    actual = interpreter.has_answer_evidence(
                        case["text"], topic_tags=frozenset(case["topic_tags"])
                    )
                elif surface == "requires_external_grounding":
                    actual = interpreter.requires_external_grounding(
                        case["text"], case["act"], initiative=case["initiative"]
                    )
                elif surface == "answer_topic_tags_for_question":
                    actual = sorted(
                        interpreter.answer_topic_tags_for_question(
                            case["text"],
                            topic_tags=frozenset(case["topic_tags"]),
                            candidate_tags=tuple(case["candidate_tags"]),
                        )
                    )
                elif surface == "has_explicit_topic_shift":
                    actual = interpreter.has_explicit_topic_shift(case["text"])
                else:
                    self.fail(f"unsupported participation surface: {surface}")
                self.assertEqual(actual, case["legacy"])

    def test_worker_rules_are_independent_and_not_in_the_data_only_archive(
        self,
    ) -> None:
        worker_root = ROOT / "worker"
        worker_files = tuple(sorted(worker_root.rglob("*.py")))
        self.assertTrue(worker_files)
        for path in worker_files:
            tree = ast.parse(path.read_text(encoding="utf-8"))
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    imports.append(node.module)
                elif isinstance(node, ast.Import):
                    imports.extend(alias.name for alias in node.names)
            with self.subTest(source=path.relative_to(ROOT).as_posix()):
                self.assertFalse(any(name.startswith("pupu_danmu") for name in imports))

        manifest_path = ROOT / "plugins" / "fabric-buyer" / "manifest.json"
        manifest = package_plugins._load_manifest(manifest_path)
        files = package_plugins._package_files(manifest_path.parent, manifest)
        archive_bytes = package_plugins._build_archive(files)
        with zipfile.ZipFile(BytesIO(archive_bytes)) as archive:
            names = archive.namelist()
        self.assertIn("manifest.json", names)
        self.assertFalse(any(name.endswith(".py") for name in names))
        self.assertFalse(any(name.startswith("worker/") for name in names))


if __name__ == "__main__":
    unittest.main()
