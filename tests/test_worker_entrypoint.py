"""SDK Replay checks for the local-only fabric Worker entrypoint."""

from __future__ import annotations

import unittest
from datetime import UTC, datetime

from pupu_danmu_plugin_sdk.host import HostStub, MockLlm
from pupu_danmu_plugin_sdk.protocol import (
    Candidate,
    Invocation,
    Opportunity,
    OpportunityMode,
    SelfSentMessage,
    SessionFocus,
    Silent,
    TypedFailure,
    ViewerChatSnapshot,
    ViewerMessage,
    encode_invocation,
)
from pupu_danmu_plugin_sdk.replay import ReplayHarness

from worker.fabric_buyer.entrypoint import run


def _invocation(
    *,
    available: bool = True,
    mode: OpportunityMode = OpportunityMode.CONTEXTUAL_FOLLOWUP,
    viewer_texts: tuple[str, ...] = ("做衬衫可以吗？",),
) -> Invocation:
    observed_at = datetime(2026, 10, 16, 8, 0, tzinfo=UTC)
    messages = tuple(
        ViewerMessage(f"viewer-{index}", text, observed_at)
        for index, text in enumerate(viewer_texts)
    )
    return Invocation(
        invocation_id="invocation-1",
        session_id="session-1",
        run_id="run-1",
        capture_id="capture-1",
        revision=1,
        viewer_chat=ViewerChatSnapshot(messages),
        session_focus=SessionFocus(current_focus="衬衫" if viewer_texts else ""),
        opportunity=Opportunity(mode=mode, available=available),
        recent_self_sent=(
            SelfSentMessage("颜色怎么样？", datetime(2026, 10, 16, 7, 59, tzinfo=UTC)),
        ),
    )


def _replay(
    invocation: Invocation,
    *responses: str,
    capabilities: tuple[str, ...] = ("chat.read", "room.read", "llm.generate"),
) -> tuple[object, MockLlm]:
    llm = MockLlm(responses)
    host = HostStub(capabilities=capabilities, llm=llm)
    record = ReplayHarness(host).run_jsonl(
        encode_invocation(invocation).decode("utf-8"), plugin=run
    )[0]
    return record.outcome, llm


class FabricWorkerEntrypointTests(unittest.TestCase):
    def test_uses_host_llm_and_keeps_viewer_and_self_sent_context_separate(
        self,
    ) -> None:
        outcome, llm = _replay(_invocation(), "垂感怎么样？")

        self.assertIsInstance(outcome, Candidate)
        self.assertEqual(outcome.text, "垂感怎么样？")
        self.assertIn("attribute:fabric_drape", outcome.semantic_tags)
        self.assertEqual(len(llm.prompts), 1)
        self.assertIn("做衬衫可以吗？", llm.prompts[0])
        self.assertIn("本插件此前已发送内容", llm.prompts[0])
        self.assertIn("颜色怎么样？", llm.prompts[0])

    def test_unavailable_opportunity_does_not_call_the_model(self) -> None:
        outcome, llm = _replay(_invocation(available=False), "垂感怎么样？")

        self.assertEqual(outcome, Silent("opportunity_unavailable"))
        self.assertEqual(llm.prompts, [])

    def test_missing_llm_capability_fails_closed(self) -> None:
        outcome, llm = _replay(_invocation(), capabilities=("chat.read", "room.read"))

        self.assertEqual(outcome, TypedFailure("capability_denied"))
        self.assertEqual(llm.prompts, [])

    def test_candidate_rejected_by_fabric_policy_becomes_silent(self) -> None:
        outcome, llm = _replay(_invocation(), "这款是纯棉的，很透气。")

        self.assertIsInstance(outcome, Silent)
        self.assertEqual(len(llm.prompts), 1)

    def test_safe_initiative_uses_the_host_opportunity_mode(self) -> None:
        invocation = _invocation(mode=OpportunityMode.SAFE_INITIATIVE, viewer_texts=())
        outcome, llm = _replay(invocation, "有适合做发圈的布料吗？")

        self.assertIsInstance(outcome, Candidate)
        self.assertEqual(outcome.text, "有适合做发圈的布料吗？")
        self.assertIn("usage:发圈", outcome.semantic_tags)
        self.assertIn("安全主动", llm.prompts[0])
        self.assertNotIn("做衬衫可以吗？", llm.prompts[0])


if __name__ == "__main__":
    unittest.main()
