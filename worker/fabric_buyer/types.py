"""Small protocol-independent value objects used by the local fabric Worker."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from typing import Protocol


class StringEnum(str, Enum):
    """String enum compatible with Python 3.10."""

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True, slots=True)
class PolicyDecision:
    allowed: bool
    reason: str | None = None
    tags: tuple[str, ...] = ()

    @classmethod
    def accept(cls, *tags: str) -> PolicyDecision:
        return cls(True, None, tuple(tags))

    @classmethod
    def reject(cls, reason: str, *tags: str) -> PolicyDecision:
        return cls(False, reason, tuple(tags))


@dataclass(frozen=True, slots=True)
class PromptPolicyProjection:
    policy_id: str
    version: int
    preferred_intents: tuple[str, ...]
    forbidden_dimensions: tuple[str, ...]
    phase_notes: tuple[str, ...]
    hard_constraints: tuple[str, ...]

    @property
    def revision(self) -> str:
        return f"{self.policy_id}.v{self.version}"


class ContextPhase(StringEnum):
    COLD_START = "cold_start"
    WARMING = "warming"
    CONTEXTUAL = "contextual"


@dataclass(frozen=True, slots=True)
class BootstrapContext:
    streamer_name: str = ""
    platform_id: str = ""


@dataclass(frozen=True, slots=True)
class ObjectiveFactClaim:
    predicate: str
    value: str

    @classmethod
    def from_candidate(
        cls, _text: str, *, subject: str, predicate: str, value: str
    ) -> ObjectiveFactClaim:
        if subject != "active_product":
            raise ValueError("unsupported fixture fact subject")
        return cls(predicate, value)


class TrustedFactSource(Protocol):
    """Marker protocol; the test fixture intentionally has no trusted source."""


class ParticipationPolicyInterpreter(Protocol):
    def resolve_participation_act(
        self, text: str, declared: str | None
    ) -> str | None: ...


class ParticipationAct(StringEnum):
    QUESTION = "question"
    SILENT = "silent"
    ACKNOWLEDGE = "acknowledge"
    PREFERENCE = "preference"
    FOLLOW = "follow"
    REACTION = "reaction"


@dataclass(frozen=True, slots=True)
class RollingQuota:
    tag: str
    window_size: int
    max_count: int

    @property
    def reason(self) -> str:
        return f"rolling_quota.{self.tag}"


@dataclass(frozen=True, slots=True)
class RollingContentPolicy:
    quotas: tuple[RollingQuota, ...] = field(default_factory=tuple)

    @property
    def tags(self) -> tuple[str, ...]:
        return tuple(quota.tag for quota in self.quotas)

    def evaluate(
        self,
        *,
        candidate_tags: Sequence[str],
        submitted_history: Sequence[Sequence[str]],
    ) -> PolicyDecision:
        candidate = {str(tag or "").strip() for tag in candidate_tags}
        candidate.discard("")
        for quota in self.quotas:
            if quota.tag not in candidate:
                continue
            window = (
                submitted_history[-(quota.window_size - 1) :]
                if quota.window_size > 1
                else ()
            )
            tagged = sum(
                1 for tags in window if quota.tag in {str(item or "") for item in tags}
            )
            if tagged + 1 > quota.max_count:
                return PolicyDecision.reject(quota.reason, *sorted(candidate))
        return PolicyDecision.accept(*sorted(candidate))


@dataclass(frozen=True, slots=True)
class TopicInterest:
    topic_id: str
    relevance: int
    related_topic_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ViewerArchetype:
    archetype_id: str
    display_name: str
    description: str
    information_needs: tuple[str, ...]
    style_tendencies: tuple[str, ...]
    topic_interests: tuple[TopicInterest, ...]
