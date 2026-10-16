"""Buyer-cloth vocabulary and deterministic participation interpretation."""

from __future__ import annotations

import re

from .archetypes import buyer_cloth_viewer_topic_tags
from .topics import has_usage_answer_evidence
from .topics import topics_in
from .types import ParticipationAct

_CHOICE_VALUE_PATTERN = (
    r"(?:纯棉|棉麻|涤纶|羊毛|真丝|亚麻|锦纶|粘纤|氨纶|棉|麻|针织|梭织|府绸|纱卡"
    r"|[黑白红蓝棕紫深浅绿黄灰橙粉米咖银金]色"
    r"|\d+(?:\.\d+)?(?:厘米|毫米|公分|米|cm|mm|号)?)(?:的)?"
)
_CHOICE_DECLARATIVE_ENDING = r"(?:都|均)(?:不|很|挺|比较)?(?:可以|行|喜欢|能用)"
_QUESTION_CUE = re.compile(
    r"\?|？|多少|多宽|多大|多长|几(?:米|个|种|件|款|支|幅)|哪(?:种|个|款|些|里)"
    r"|什么|怎么|如何|有没有|会不会|要不要|能不能|可不可以|是否|吗|呢(?=\s*(?:$|[，,。；;！？?!]))"
    r"|是不是|能否|可否|好不好|行不行|含不含|透不透|对不对|合不合适|适不适合"
    rf"|{_CHOICE_VALUE_PATTERN}\s*还是\s*{_CHOICE_VALUE_PATTERN}"
    rf"(?![^，,。；;！？?]*{_CHOICE_DECLARATIVE_ENDING}"
    rf"|\s*[,，]\s*(?:我|我们)?\s*{_CHOICE_DECLARATIVE_ENDING})"
)
_PREFERENCE_CUE = re.compile(r"更喜欢|更倾向|偏爱|我会选|我选|比较喜欢|更看重")
_AGREEMENT_CUE = re.compile(r"也认同|认同|也是|确实|说得对|同意|我也|是的")
_ACKNOWLEDGE_CUE = re.compile(
    r"收到|明白|了解|懂了|确实|原来如此|说得对|是的|嗯嗯|认同"
)
_FOLLOW_CUE = re.compile(r"接着|继续|那|另外|再问|顺便")
_NON_ANSWER_CUE = re.compile(
    r"关注|看重|喜欢|倾向|想要|想买|第一次|用过|不知道|不清楚"
    r"|应该|可能|也许|如果|假如|好像|似乎"
    r"|(?:我|我们)(?:还)?(?:有|没有|没)"
)
_MATERIAL_PATTERN = r"(?>纯棉|棉麻|棉|涤纶|羊毛|真丝|亚麻|锦纶|粘纤|氨纶)"
_COMPOSITION_RATIO_PATTERN = (
    r"(?:百分之[\d一二两三四五六七八九十百]+|\d+(?:\.\d+)?[%％]"
    r"|[一二两三四五六七八九十]+成)"
)
_COMPOSITION_ANSWER_EVIDENCE = re.compile(
    # Accepting either material does not assert the actual composition.
    rf"^(?!.*{_CHOICE_VALUE_PATTERN}\s*还是\s*{_CHOICE_VALUE_PATTERN}).*?(?:"
    rf"(?:是|为|含(?:有)?|包含){_COMPOSITION_RATIO_PATTERN}?{_MATERIAL_PATTERN}"
    r"(?!感|的?(?:手感|触感))"
    rf"|{_COMPOSITION_RATIO_PATTERN}{_MATERIAL_PATTERN}(?!感|的?(?:手感|触感))"
    rf"|{_MATERIAL_PATTERN}(?:含量|比例)?{_COMPOSITION_RATIO_PATTERN}"
    r")"
)
_ATTRIBUTE_ANSWER_EVIDENCE: tuple[tuple[frozenset[str], re.Pattern[str]], ...] = (
    (frozenset({"composition"}), _COMPOSITION_ANSWER_EVIDENCE),
    (
        frozenset({"dimensions", "fabric_width"}),
        re.compile(
            r"(?:门幅|幅宽|宽幅|宽度|尺寸|拼幅)[^，。]{0,6}?"
            r"[\d零〇一二两三四五六七八九十百半]+(?:\.\d+)?"
            r"(?:厘米|毫米|公分|米|cm|mm)?(?:宽|长|高)?"
            r"(?:左右|上下|的)?(?:哦|啊|呀)?$",
            re.IGNORECASE,
        ),
    ),
    (
        frozenset({"yardage"}),
        re.compile(
            r"(?:用量|米数)[^，。]{0,6}?[\d零〇一二两三四五六七八九十百半]+"
            r"(?:\.\d+)?米?(?:左右|上下|就够|够)?(?:了|的|哦|啊|呀)?$"
        ),
    ),
    (
        frozenset({"stretch"}),
        re.compile(
            r"(?:四面|两面|双向|单向)弹|(?:有|没|没有|不带)弹力|不弹"
            r"|弹力(?:是)?(?:很|挺|比较|非常|还|不)?(?:好|大|小|强|弱|足|一般|不错)"
        ),
    ),
    (
        frozenset({"softness"}),
        re.compile(
            r"(?:很|挺|比较|偏)(?:软|硬)|柔软|硬挺"
            r"|(?:很|挺|比较|特别)亲肤|亲肤(?:的|性好|不错)"
        ),
    ),
    (
        frozenset({"breathability"}),
        re.compile(
            r"(?:很|挺|比较|不)透气|透气的|不闷"
            r"|透气(?:性)?(?:很|挺|比较|还)?(?:好|强|差|一般|不错|可以)"
        ),
    ),
    (
        frozenset({"fabric_drape"}),
        re.compile(r"有垂感|垂坠|垂感(?:很|挺|比较|非常)?(?:好|强|差|一般|不错)"),
    ),
    (
        frozenset({"color", "fabric_color"}),
        re.compile(
            r"[黑白红蓝棕紫深浅绿黄灰橙粉米咖银金]色"
            r"|(?:颜色|色号)(?:是|有|为)[\d一二两三四五六七八九十]+(?:种|款|号)"
        ),
    ),
    (
        frozenset({"pattern"}),
        re.compile(
            r"玫瑰花|碎花|条纹|波点|格子|(?:花型|花纹)(?:是|有|为)"
            r"[\d一二两三四五六七八九十]+(?:号|种|款)"
        ),
    ),
    (frozenset({"current_item"}), re.compile(r"\d{1,3}号|^\d{1,3}$")),
)
_TOPIC_SHIFT = re.compile(r"换(?:个|一个|成|到|颜色|花型)|再聊|转(?:到|个话题)|接着看")
_USAGE_QUESTION_CUE = re.compile(
    r"合适|适合|(?:可不可以|能不能|能否|可否|可以|不能|能|可)做"
)
_ATTRIBUTE_VALUE_QUESTION_CUE = re.compile(
    r"多少|多宽|多大|多长|几(?:米|个|种|件|款|支|幅)"
)


class BuyerClothParticipationInterpreter:
    """Pure participation rules for the built-in buyer-cloth policy pack."""

    __slots__ = ()

    def viewer_topic_tags(self, text: str) -> tuple[str, ...]:
        return buyer_cloth_viewer_topic_tags(text)

    def resolve_participation_act(self, text: str, declared: str | None) -> str | None:
        try:
            act = ParticipationAct(str(declared or "").strip().lower())
        except ValueError:
            act = None
        if _QUESTION_CUE.search(text):
            return ParticipationAct.QUESTION.value
        if act is ParticipationAct.SILENT:
            return None
        if _AGREEMENT_CUE.search(text):
            return ParticipationAct.ACKNOWLEDGE.value
        if _PREFERENCE_CUE.search(text):
            return ParticipationAct.PREFERENCE.value
        if _ACKNOWLEDGE_CUE.search(text):
            return ParticipationAct.ACKNOWLEDGE.value
        if _FOLLOW_CUE.search(text):
            return ParticipationAct.FOLLOW.value
        if act in {
            ParticipationAct.REACTION,
            ParticipationAct.PREFERENCE,
            ParticipationAct.ACKNOWLEDGE,
            ParticipationAct.FOLLOW,
        }:
            return act.value
        return ParticipationAct.REACTION.value

    def requires_external_grounding(
        self, text: str, act: str | None, *, initiative: bool
    ) -> bool:
        if act in {"reaction", "acknowledge", "follow"} or _AGREEMENT_CUE.search(text):
            return True
        return act == "question" and not initiative

    def answer_topic_tags_for_question(
        self,
        text: str,
        *,
        topic_tags: frozenset[str],
        candidate_tags: tuple[str, ...],
    ) -> frozenset[str]:
        """Keep precise uses for suitability debt; attribute debt stays independent."""

        # An attributive fabric description is context, not the requested slot.
        description, separator, focus = (
            re.split(r"(的(?:面料|布料|布))", text, maxsplit=1)
            if re.search(r"的(?:面料|布料|布)", text)
            else ("", "", text)
        )
        focused_topics = frozenset(self.viewer_topic_tags(focus))
        if separator and focused_topics and _QUESTION_CUE.search(description) is None:
            topic_tags = focused_topics
            candidate_tags = tuple(
                tag
                for tag in candidate_tags
                if not tag.startswith("attribute:")
                or tag.removeprefix("attribute:") in focused_topics
            )
            text = focus
        attributes = frozenset(
            tag.removeprefix("attribute:")
            for tag in candidate_tags
            if tag.startswith("attribute:")
        )
        # These properties remain the requested evidence even in a use context.
        properties = (attributes or topic_tags) & {
            "breathability",
            "softness",
            "stretch",
            "fabric_drape",
        }
        if properties and _ATTRIBUTE_VALUE_QUESTION_CUE.search(text) is None:
            return frozenset(properties)
        usages = frozenset(f"usage:{topic.name}" for topic in topics_in(text))
        if (
            usages
            and _USAGE_QUESTION_CUE.search(text) is not None
            and _ATTRIBUTE_VALUE_QUESTION_CUE.search(text) is None
        ):
            return topic_tags | usages
        if attributes:
            return attributes
        return topic_tags

    def has_answer_evidence(
        self, text: str, *, topic_tags: frozenset[str] = frozenset()
    ) -> bool:
        """Require evidence for the pending attribute, not an unrelated verb/value."""

        usage_tags = frozenset(
            tag.removeprefix("usage:") for tag in topic_tags if tag.startswith("usage:")
        )
        patterns = (
            ()
            if usage_tags
            else tuple(
                pattern
                for topics, pattern in _ATTRIBUTE_ANSWER_EVIDENCE
                if topics & topic_tags
            )
        )
        # Questions and personal asides only disqualify their own clause.
        # Keep question marks attached so an interrogative fact cannot become evidence.
        return any(
            _QUESTION_CUE.search(clause) is None
            and _NON_ANSWER_CUE.search(clause) is None
            and (
                any(pattern.search(clause.strip()) is not None for pattern in patterns)
                or has_usage_answer_evidence(clause, usage_tags=usage_tags)
            )
            for clause in re.split(r"[，,。；;！!]|(?<=[？?])", text)
        )

    def has_explicit_topic_shift(self, text: str) -> bool:
        return (
            _QUESTION_CUE.search(text) is None and _TOPIC_SHIFT.search(text) is not None
        )


BUYER_CLOTH_PARTICIPATION_INTERPRETER = BuyerClothParticipationInterpreter()
