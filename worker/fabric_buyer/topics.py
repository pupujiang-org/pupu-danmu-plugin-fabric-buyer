"""Plugin-owned fabric topic vocabulary and participation evidence rules."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .types import StringEnum


class UsagePriority(StringEnum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    RARE = "rare"


@dataclass(frozen=True, slots=True)
class UsageTopic:
    name: str
    priority: UsagePriority
    aliases: tuple[str, ...] = ()


USAGE_TOPICS: tuple[UsageTopic, ...] = (
    UsageTopic("发圈", UsagePriority.PRIMARY),
    UsageTopic("连衣裙", UsagePriority.PRIMARY),
    UsageTopic("裤子", UsagePriority.PRIMARY, ("长裤", "短裤")),
    UsageTopic("衬衫", UsagePriority.PRIMARY),
    UsageTopic("半身裙", UsagePriority.PRIMARY, ("半身长裙", "半身短裙")),
    UsageTopic("外套", UsagePriority.PRIMARY),
    UsageTopic(
        "包包",
        UsagePriority.PRIMARY,
        ("包", "布包", "手提袋", "手提包", "背包", "做包"),
    ),
    *(
        UsageTopic(name, UsagePriority.SECONDARY)
        for name in (
            "上衣",
            "睡衣",
            "家居服",
            "马甲",
            "防晒衣",
            "背心",
            "罩衫",
            "打底衫",
            "袖套",
        )
    ),
    UsageTopic("围裙", UsagePriority.RARE),
    UsageTopic("窗帘", UsagePriority.RARE),
    UsageTopic("桌布", UsagePriority.RARE),
    UsageTopic("抱枕套", UsagePriority.RARE, ("枕套", "抱枕")),
    UsageTopic("坐垫", UsagePriority.RARE, ("椅垫",)),
    UsageTopic("沙发垫", UsagePriority.RARE, ("飘窗垫",)),
    UsageTopic("收纳袋", UsagePriority.RARE),
    UsageTopic("玩偶", UsagePriority.RARE),
)


_BAG_ALIAS_RE = re.compile(r"(?<!打)包(?!邮|装|括|含|裹|边)")
_BAG_ALIAS_PATTERNS = {
    "包": _BAG_ALIAS_RE,
    "做包": re.compile(rf"做{_BAG_ALIAS_RE.pattern}"),
}


def _usage_answer_pattern(topic: UsageTopic) -> re.Pattern[str]:
    aliases = "|".join(
        _BAG_ALIAS_PATTERNS[alias].pattern
        if alias in _BAG_ALIAS_PATTERNS
        else re.escape(alias)
        for alias in (topic.name, *topic.aliases)
    )
    target = rf"(?:儿童|小朋友|宝宝|小孩)?(?:{aliases})"
    return re.compile(
        rf"{target}(?:是|也|很|挺|比较|非常|还|不|并不|太)*(?:适合|合适|可以做|不能做)"
        rf"|(?:不)?(?:适合|合适)(?:用来|拿来)?(?:做|制作)?{target}"
        rf"|(?:可以|不能|能|可)(?:用来|拿来)?(?:做|制作){target}"
    )


_USAGE_ANSWER_PATTERNS = tuple(
    (topic.name, _usage_answer_pattern(topic)) for topic in USAGE_TOPICS
)


def has_usage_answer_evidence(text: str, *, usage_tags: frozenset[str]) -> bool:
    """Bind a suitability assertion to the queried use, including its aliases."""
    return any(
        name in usage_tags and pattern.search(text) is not None
        for name, pattern in _USAGE_ANSWER_PATTERNS
    )


def topics_in(text: str) -> tuple[UsageTopic, ...]:
    """归一化明确用途；「包邮」及裸「长裙」不算买布用途。"""

    value = str(text or "")
    return tuple(
        topic
        for topic in USAGE_TOPICS
        if any(
            (
                _BAG_ALIAS_PATTERNS[alias].search(value) is not None
                if alias in _BAG_ALIAS_PATTERNS
                else alias in value
            )
            for alias in (topic.name, *topic.aliases)
        )
    )


def priority_for(text: str) -> UsagePriority | None:
    priorities = {topic.priority for topic in topics_in(text)}
    for priority in (
        UsagePriority.RARE,
        UsagePriority.SECONDARY,
        UsagePriority.PRIMARY,
    ):
        if priority in priorities:
            return priority
    return None
