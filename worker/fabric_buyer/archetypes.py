"""Buyer-cloth viewer interests and their industry-owned chat topic tags."""

from __future__ import annotations

import re

from .topics import topics_in
from .types import TopicInterest
from .types import ViewerArchetype

GARMENT_MAKER = ViewerArchetype(
    archetype_id="garment_maker",
    display_name="服装手作爱好者",
    description="长期关注服装制作相关的布料用途与参数。",
    information_needs=("用途是否合适", "门幅、垂感、弹力和用量"),
    style_tendencies=("简短、具体", "先围绕当前服装用途"),
    topic_interests=(
        TopicInterest(
            "garment", 95, ("fabric_width", "fabric_drape", "stretch", "yardage")
        ),
        TopicInterest("fabric_width", 85, ("garment",)),
        TopicInterest("fabric_drape", 85, ("garment",)),
        TopicInterest("stretch", 80, ("garment",)),
        TopicInterest("yardage", 75, ("garment",)),
        TopicInterest("composition", 50, ("garment",)),
        TopicInterest("family_clothing", 35),
        TopicInterest("craft", 45),
        TopicInterest("home_textile", 15),
        TopicInterest("color", 25),
        TopicInterest("softness", 45),
        TopicInterest("breathability", 35),
    ),
)

CRAFTER = ViewerArchetype(
    archetype_id="crafter",
    display_name="手作人",
    description="长期关注适合裁剪和制作小件的布料信息。",
    information_needs=("是否好裁", "软硬、幅宽和用途"),
    style_tendencies=("简短、直接", "围绕手作材料本身"),
    topic_interests=(
        TopicInterest(
            "craft", 95, ("fabric_width", "softness", "stretch", "composition")
        ),
        TopicInterest("fabric_width", 75, ("craft",)),
        TopicInterest("softness", 75, ("craft",)),
        TopicInterest("stretch", 70, ("craft",)),
        TopicInterest("composition", 65, ("craft",)),
        TopicInterest("garment", 50),
        TopicInterest("family_clothing", 50),
        TopicInterest("home_textile", 25),
        TopicInterest("color", 35),
        TopicInterest("fabric_drape", 45),
        TopicInterest("yardage", 70, ("craft",)),
        TopicInterest("breathability", 40),
    ),
)

FAMILY_CRAFT = ViewerArchetype(
    archetype_id="family_craft",
    display_name="亲子手作爱好者",
    description="长期关注亲子手作与儿童衣物相关的布料信息。",
    information_needs=("亲肤、柔软和透气", "用途是否适合儿童衣物"),
    style_tendencies=("简短、实用", "不声称拥有孩子或相关经历"),
    topic_interests=(
        TopicInterest(
            "family_clothing",
            98,
            ("softness", "breathability", "composition", "fabric_width"),
        ),
        TopicInterest("softness", 85, ("family_clothing",)),
        TopicInterest("breathability", 85, ("family_clothing",)),
        TopicInterest("composition", 75, ("family_clothing",)),
        TopicInterest("fabric_width", 65, ("family_clothing",)),
        TopicInterest("craft", 75, ("family_clothing",)),
        TopicInterest("garment", 40),
        TopicInterest("home_textile", 30),
        TopicInterest("color", 25),
        TopicInterest("fabric_drape", 25),
        TopicInterest("stretch", 40),
        TopicInterest("yardage", 45),
    ),
)

HOME_TEXTILE = ViewerArchetype(
    archetype_id="home_textile",
    display_name="家居布艺爱好者",
    description="长期关注床品、窗帘和家居布艺的尺寸与材料信息。",
    information_needs=("门幅与尺寸", "材质和柔软度"),
    style_tendencies=("简短、具体", "围绕当前家居用途"),
    topic_interests=(
        TopicInterest(
            "home_textile",
            98,
            ("dimensions", "fabric_width", "composition", "softness"),
        ),
        TopicInterest("dimensions", 90, ("home_textile",)),
        TopicInterest("fabric_width", 85, ("home_textile",)),
        TopicInterest("composition", 75, ("home_textile",)),
        TopicInterest("softness", 75, ("home_textile",)),
        TopicInterest("breathability", 65, ("home_textile",)),
        TopicInterest("garment", 20),
        TopicInterest("family_clothing", 25),
        TopicInterest("craft", 35),
        TopicInterest("color", 35),
        TopicInterest("fabric_drape", 30),
        TopicInterest("stretch", 20),
        TopicInterest("yardage", 55),
    ),
)

BEGINNER_BUYER = ViewerArchetype(
    archetype_id="beginner_buyer",
    display_name="入门买布用户",
    description="长期关注常见布料用途和容易理解的基础参数。",
    information_needs=("常见用途是否合适", "简单、明确的基础参数"),
    style_tendencies=("简短、通俗", "避免复杂工艺术语"),
    topic_interests=(
        TopicInterest("garment", 70, ("fabric_width", "composition", "softness")),
        TopicInterest("craft", 70, ("fabric_width", "composition", "softness")),
        TopicInterest("family_clothing", 55),
        TopicInterest(
            "home_textile", 60, ("dimensions", "fabric_width", "composition")
        ),
        TopicInterest("fabric_width", 65, ("garment", "craft", "home_textile")),
        TopicInterest("composition", 60, ("garment", "craft", "home_textile")),
        TopicInterest("softness", 65, ("garment", "craft", "home_textile")),
        TopicInterest("breathability", 50),
        TopicInterest("dimensions", 60, ("home_textile",)),
        TopicInterest("color", 35),
        TopicInterest("fabric_drape", 35),
        TopicInterest("stretch", 40),
        TopicInterest("yardage", 50),
    ),
)

BUYER_CLOTH_VIEWER_ARCHETYPES = (
    GARMENT_MAKER,
    CRAFTER,
    FAMILY_CRAFT,
    HOME_TEXTILE,
    BEGINNER_BUYER,
)

_TOPIC_TERMS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "family_clothing",
        (
            "小朋友衣服",
            "小朋友睡衣",
            "儿童衣服",
            "童装",
            "小孩",
            "小朋友",
            "宝宝衣服",
            "儿童睡衣",
        ),
    ),
    (
        "home_textile",
        (
            "四件套",
            "床单",
            "床笠",
            "被套",
            "枕套",
            "床品",
            "窗帘",
            "桌布",
            "抱枕",
            "坐垫",
            "沙发垫",
        ),
    ),
    (
        "garment",
        (
            "连衣裙",
            "半身裙",
            "衬衫",
            "裤子",
            "长裤",
            "短裤",
            "外套",
            "上衣",
            "睡衣",
            "家居服",
        ),
    ),
    ("craft", ("发圈", "包包", "布包", "手提袋", "收纳袋", "玩偶", "小物")),
    ("dimensions", ("尺寸", "拼幅", "做多大", "多长", "多宽")),
    ("fabric_width", ("门幅", "幅宽", "宽幅", "宽度")),
    ("fabric_drape", ("垂感", "垂坠")),
    ("stretch", ("弹力", "有弹", "不弹")),
    ("yardage", ("用量", "几米", "多少米", "米数")),
    (
        "composition",
        ("纯棉", "棉麻", "成分", "材质", "涤纶", "含棉", "棉含量", "%棉", "％棉"),
    ),
    ("softness", ("柔软", "软不软", "软硬", "亲肤")),
    ("breathability", ("透气", "闷不闷")),
    (
        "color",
        (
            "黑色",
            "白色",
            "红色",
            "蓝色",
            "颜色",
            "色号",
            "花色",
            "棕色",
            "棕色系",
            "紫色",
            "深色",
            "浅色",
        ),
    ),
    ("pattern", ("花型", "花纹", "玫瑰花", "碎花", "条纹", "波点")),
)


def buyer_cloth_viewer_topic_tags(text: str) -> tuple[str, ...]:
    """Classify only stable, explicit buyer-cloth topic tags."""

    value = str(text or "")
    # Aliases carry the same broad topic as their existing canonical use.
    values = (value, *(topic.name for topic in topics_in(value)))
    tags = tuple(
        topic_id
        for topic_id, terms in _TOPIC_TERMS
        if any(term in item for item in values for term in terms)
    )

    if re.fullmatch(r"\d{1,3}", value.strip()) or re.search(
        r"(?:看看|看|要|第)?\d{1,3}号", value
    ):
        tags = (*tags, "current_item")
    return tags


__all__ = [
    "BEGINNER_BUYER",
    "BUYER_CLOTH_VIEWER_ARCHETYPES",
    "CRAFTER",
    "FAMILY_CRAFT",
    "GARMENT_MAKER",
    "HOME_TEXTILE",
    "buyer_cloth_viewer_topic_tags",
]
