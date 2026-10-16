"""Independent deterministic rules for the fabric-buyer Worker prototype.

This module has no host-domain imports or external capabilities. It supplies policy
logic only; the current official ZIP remains data-only and does not include it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .archetypes import BUYER_CLOTH_VIEWER_ARCHETYPES
from .archetypes import buyer_cloth_viewer_topic_tags
from .participation import BUYER_CLOTH_PARTICIPATION_INTERPRETER
from .topics import UsagePriority
from .topics import priority_for
from .topics import topics_in
from .types import BootstrapContext
from .types import ContextPhase
from .types import ObjectiveFactClaim
from .types import ParticipationPolicyInterpreter
from .types import PolicyDecision
from .types import PromptPolicyProjection
from .types import RollingContentPolicy
from .types import RollingQuota
from .types import StringEnum
from .types import TrustedFactSource
from .types import ViewerArchetype

BUYER_CLOTH_POLICY_ID = "buyer_cloth"
BUYER_CLOTH_POLICY_VERSION = 3

# ---------------------------------------------------------------------------
# 稳定拒绝码
# ---------------------------------------------------------------------------
#: 它们会进日志与快照,所以是稳定标识而不是文案。
REASON_EMPTY = "buyer_cloth.empty"
REASON_DISCOUNT = "buyer_cloth.discount_inducement"
REASON_METER_OVER_LIMIT = "buyer_cloth.meter_over_limit"
REASON_METER_STATEMENT = "buyer_cloth.meter_statement"
REASON_PRAISE_WITHOUT_QUESTION = "buyer_cloth.praise_without_question"
REASON_OBJECTIVE_CLAIM = "buyer_cloth.objective_claim"
REASON_DISABLED_DIMENSION = "buyer_cloth.disabled_attribute_dimension"
REASON_COMMITMENT = "buyer_cloth.commitment"
REASON_THREAD_OVER_LIMIT = "buyer_cloth.thread_count_over_limit"
REASON_USAGE_ATTRIBUTE = "buyer_cloth.usage_attribute_mismatch"
REASON_MIXED_SELECTION = "buyer_cloth.mixed_selection"
REASON_FORBIDDEN_TERM = "buyer_cloth.forbidden_term"
REASON_QUALITY_RISK = "buyer_cloth.quality_risk"
REASON_EMOTION_PERFORMANCE = "buyer_cloth.emotion_performance"
REASON_NARROW_STYLE = "buyer_cloth.narrow_style"
REASON_MARKETING_COLOUR = "buyer_cloth.marketing_colour"
REASON_METHOD_QUESTION = "buyer_cloth.method_question"
REASON_OPEN_QUESTION = "buyer_cloth.open_question"
REASON_SUBJECTIVE_FEEL = "buyer_cloth.subjective_feel"
REASON_WEAVE_TERMINOLOGY = "buyer_cloth.weave_terminology"
REASON_META_NEED = "buyer_cloth.method_meta_need"
REASON_META_SELECTION = "buyer_cloth.meta_selection"
REASON_VAGUE_SCOPE = "buyer_cloth.vague_scope"
REASON_FLOW_NARRATION = "buyer_cloth.flow_narration"
REASON_SELF_NARRATION = "buyer_cloth.self_narration"
REASON_FINISHED_GARMENT_TOPIC = "buyer_cloth.finished_garment_topic"
REASON_UNGROUNDED_REFERENCE = "buyer_cloth.ungrounded_reference"

#: Cold Start 提示词里的稳定 token;渲染提示词的实现**不得**自创语义。
NOTE_COLD_START_SAFE = "cold_start_no_observed_facts"
NOTE_NO_FACT_CLAIM = "never_claim_product_facts"
NOTE_ASK_NOT_ASSERT = "ask_rather_than_assert"
NOTE_MIX_GUIDANCE = "usage_priority_primary_secondary_rare"
NOTE_GROUNDED = "may_reference_observed_chat"


class AttributeDimension(StringEnum):
    """商品属性维度。

    用维度而不是中文黑名单表达"这个属性现在不能聊":以后某个行业重新允许重量,
    改的是规则数据里的一行,而不是散落在各处的字面量。
    """

    WEIGHT = "weight"
    WIDTH = "width"
    THREAD_COUNT = "thread_count"
    COMPOSITION = "composition"
    STRETCH = "stretch"
    FEEL = "feel"
    COLOUR = "colour"
    PATTERN = "pattern"


# ---------------------------------------------------------------------------
# 词表与用途分组
# ---------------------------------------------------------------------------

GARMENT_USAGES: tuple[str, ...] = (
    "发圈",
    "裤子",
    "衬衫",
    "上衣",
    "半身裙",
    "连衣裙",
    "睡衣",
    "家居服",
    "短裤",
    "长裤",
    "马甲",
    "防晒衣",
    "外套",
    "围裙",
    "袖套",
    "背心",
    "罩衫",
    "长裙",
    "短裙",
    "打底衫",
)
HOME_USAGES: tuple[str, ...] = (
    "窗帘",
    "抱枕套",
    "枕套",
    "抱枕",
    "坐垫",
    "椅垫",
    "桌布",
    "沙发垫",
    "飘窗垫",
)
CRAFT_USAGES: tuple[str, ...] = ("布包", "手提袋", "收纳袋", "玩偶")
#: 童装与宠物是稀有话题:不进入通用用途池,只按配额少量出现。它们与上面三组
#: 互斥,旧仓库的测试也断言"一条只属于一个组"。
SPECIAL_MARKERS: tuple[str, ...] = (
    "童装",
    "宠物衣服",
    "小孩",
    "娃",
    "小狗",
    "狗窝",
    "狗垫",
)
LACE_TERMS: tuple[str, ...] = ("花边", "蕾丝")

#: 家用布艺不能问的属性:坐垫的"弹力/支数"不是买家会问的东西。
HOME_FORBIDDEN_ATTRIBUTES: tuple[str, ...] = ("弹力", "支数", "针织还是梭织")
#: 手工件的同理。
CRAFT_FORBIDDEN_ATTRIBUTES: tuple[str, ...] = ("弹力", "支数", "垂感")
#: (用途, 不能与该用途同句的属性或做法)
USAGE_ATTRIBUTE_CONFLICTS: tuple[tuple[str, str], ...] = (
    ("睡衣", "挺一点"),
    ("家居服", "挺一点"),
    ("打底衫", "挺一点"),
    ("围裙", "弹力"),
    ("防晒衣", "挺一点"),
    ("袖套", "挺一点"),
    ("玩偶", "门幅"),
    ("玩偶", "幅宽"),
    ("玩偶", "加衬"),
    ("打底衫", "棉麻"),
    ("打底衫", "平纹"),
    ("打底衫", "斜纹"),
    ("宠物衣服", "幅宽"),
)

#: 把筛选能力当买家话术:直播间里没人这么说话。
MIXED_SELECTION_TERMS: tuple[str, ...] = (
    "选面料还是颜色",
    "选门幅还是克重",
    "颜色和花型能分开选吗",
    "布边可以一起要吗",
    "准备做的话看哪些参数",
    "选布时要问哪些",
)

#: 销售与生活类:直播间的自动弹幕不该谈价、也不该演生活。
FORBIDDEN_TERMS: tuple[str, ...] = (
    "优惠",
    "满减",
    "赠品",
    "便宜",
    "划算",
    "底价",
    "折扣",
    "优惠券",
    "秒杀",
    "改价",
    "快递",
    "下班",
    "加班",
    "地铁",
    "吃饭",
    "睡觉",
    "天气",
    "下雨",
    "主播辛苦",
    "主播加油",
    "喝口水",
)
#: 质量风险:只有买家自己会提,自动弹幕提它等于替主播招黑。
QUALITY_RISK_TERMS: tuple[str, ...] = (
    "掉色",
    "缩水",
    "会不会缩",
    "洗了会缩",
    "下水会缩",
    "起球",
    "变形",
    "异味",
    "扎皮肤",
    "勾丝",
    "开裂",
    "质量问题",
    "售后",
    "色差",
)
#: 情绪表演:像营销号,不像观众。
EMOTION_TERMS: tuple[str, ...] = (
    "第一眼",
    "有点喜欢",
    "心动",
    "种草",
    "舍不得划走",
    "反复看",
    "眼睛移不开",
    "手一直停",
)
#: 窄风格词:它们把商品往一个很窄的审美上定义,不是零售买家的问法。
NARROW_STYLE_TERMS: tuple[str, ...] = (
    "很仙",
    "仙气",
    "甜美",
    "甜酷",
    "复古",
    "文艺",
    "清新",
    "喜庆",
    "少女感",
    "法式",
    "国风",
    "森系",
    "显白",
    "显瘦",
)
#: 营销色名:库里的色名是平白说法(浅棕、灰蓝),这些是带货话术。
MARKETING_COLOUR_TERMS: tuple[str, ...] = (
    "藕粉色",
    "豆沙色",
    "雾蓝色",
    "橄榄绿色",
    "砖红色",
    "酒红色",
    "燕麦色",
    "卡其色",
    "藏蓝色",
    "藏青色",
    "米灰色",
    "灰紫色",
    "暖白色",
    "冷白色",
    "奶黄色",
    "灰棕色",
    "杏色",
    "青灰色",
    "墨绿色",
    "浅卡其色",
    "深咖色",
)
#: 承诺/成交:自动弹幕不能替任何人下单。
COMMITMENT_TERMS: tuple[str, ...] = (
    "我要",
    "先来",
    "给我留",
    "我拍",
    "已经买",
    "买过",
    "家里就有",
    "马上拍",
    "下单",
    "回购",
    "购物车",
    "全要了",
    "帮我裁",
)

#: 共享的"是否构成提问"判据。改成两套正则必然走神,所以只有这一份。
GENUINE_QUESTION_PATTERN = (
    r"(?:吗|么)$|什么|多少|多大|几(?:米|个|种|件|款|层|支|档|块)|"
    r"哪(?:种|个|些|里|款|类|项|边)|怎么|如何|有没有|多重|多宽|够不够|"
    r"能不能|可不可以|要不要|能否|可否|是不是|"
    r"(?:是|偏|用|选)[^，]{0,12}还是"
)
#: 引导降价:表达"要更便宜"的意图。
DISCOUNT_INDUCEMENT_PATTERN = (
    r"买[^，。]{0,8}?(?:送|赠|打折|九折|八折|减)"
    r"|满[^，。]{0,8}?(?:减|送|打折)"
    r"|第二件|半价|凑单|凑满|加送"
    r"|打折|优惠|满减|折扣|赠品|券|便宜|划算|底价|改价|秒杀"
)
#: 宽泛夸赞必须落在具体选购问题上,否则就是空话。
PRAISE_TERMS: tuple[str, ...] = ("好看", "不错", "顺眼", "耐看", "有质感", "质感不错")
BUYING_TOPIC_PATTERN = (
    r"做|面料|颜色|纯色|花色|素色|支|克|幅宽|弹力|针织|梭织|几米|多少|还有|"
    r"叫什么|选|成分|纯棉|棉麻|材质|纱卡|府绸|提花|手感"
)
#: "这个/这款"开头的客观属性只能提问,不能替商品下结论。
OBJECTIVE_TOPIC_PATTERN = (
    r"支|克重|幅宽|门幅|面料|成分|弹力|针织|梭织|纯棉|棉麻|厚|薄|软|挺|垂"
)
#: 禁用属性维度的词面(维度 → 触发词)。
DISABLED_DIMENSION_TERMS: tuple[tuple[AttributeDimension, tuple[str, ...]], ...] = (
    # 克重族整族下线。它是可配置的维度,而不是"含某个汉字就拒"。
    (AttributeDimension.WEIGHT, ("克重", "克", "重量")),
)
#: 纯自述:"准备/想先/先看看…" 开头,又没有真问题与用途名词。
SELF_NARRATION_PATTERN = r"^(?:准备|想先|先看看|先挑挑|先问)"
#: 用途名词判据(自述弹幕的兜底:提到具体用途就不算空话)。
USAGE_NOUN_PATTERN = "|".join(
    re.escape(item)
    for item in (*GARMENT_USAGES, *HOME_USAGES, *CRAFT_USAGES, *SPECIAL_MARKERS)
)

_BANKS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (REASON_FORBIDDEN_TERM, FORBIDDEN_TERMS),
    (REASON_QUALITY_RISK, QUALITY_RISK_TERMS),
    (REASON_EMOTION_PERFORMANCE, EMOTION_TERMS),
    (REASON_NARROW_STYLE, NARROW_STYLE_TERMS),
    (REASON_MARKETING_COLOUR, MARKETING_COLOUR_TERMS),
)

#: 句族判据:(拒绝码, 正则)。**有序**:一条候选同时命中多条时,报第一条。
PATTERN_RULES: tuple[tuple[str, str], ...] = (
    (
        REASON_FINISHED_GARMENT_TOPIC,
        r"版型|尺码|码数|偏大|偏小|宽松|修身|显瘦|合身|围度|腰围|胸围|肩宽|臀围|袖长|裤腰"
        r"|衣长|裤长|穿搭|上身效果|穿着效果"
        r"|(?:搭配|配)[^，。！？]{0,8}(?:裤|裙|衬衫|上衣)",
    ),
    (
        REASON_METHOD_QUESTION,
        r"(?:怎么|如何)(?:定|选|挑|判断|搭配|估|算|比较|区分"
        r"|分档|一起看|一起判断|一起选|一起问)"
        r"|先(?:看|问)[^，]{0,10}还是"
        r"|从哪(?:档|项|类|种|款)"
        r"|要问(?:到)?什么程度|需要(?:先)?问吗|要不要先问|要先问吗"
        r"|先(?:看|问)哪|先看什么",
    ),
    (
        REASON_OPEN_QUESTION,
        r"不足(?:时|的)|不合适时|不够(?:宽|长|大|用)?时|万一"
        r"|一般(?:怎么|如何|看哪些)|通常(?:怎么|如何)"
        r"|重点看什么|应该先问|先问什么"
        r"|怎么一起(?:估|看|挑|判断)|要一起看吗"
        r"|要留意吗|需要留意吗|需要留意|需要注意吗|要注意吗"
        r"|有关系吗|有影响吗"
        r"|有什么区别|怎么区分|如何区分|差别大吗|哪个更",
    ),
    (
        REASON_SUBJECTIVE_FEEL,
        r"偏哪(?:一)?边"
        r"|(?:需要|要|用不用|要不要)看(?:手感|触感)"
        r"|(?:手感|触感)(?:能|可以)?分几档",
    ),
    (REASON_WEAVE_TERMINOLOGY, r"织法"),
    (REASON_META_NEED, r"需要(?:特别)?看吗|要看吗|有必要吗"),
    (
        REASON_META_SELECTION,
        r"^(?:可以按|颜色选择可以按|颜色可以按|花型可以按|门幅可以按)"
        r".*(?:看吗|筛选吗|推荐几种吗)$",
    ),
    (
        REASON_META_SELECTION,
        r"(?:可以(?:先)?按|能不能按)"
        r"(?:用途|成分|织法|厚薄|颜色|花型|门幅|手感|弹力|支数)",
    ),
    (REASON_VAGUE_SCOPE, r"小件|小物|小项目"),
    (REASON_FLOW_NARRATION, r"再(?:选|挑|决定|做|看|问|比较|估|算|裁|买)"),
)

#: 现有商品属性词的"宽泛命中"集合(旧校验器用同一份,这里保持逐字一致)。
_BUYING_TOPIC_RE = re.compile(BUYING_TOPIC_PATTERN)
_OBJECTIVE_TOPIC_RE = re.compile(OBJECTIVE_TOPIC_PATTERN)
_DANGLING_REFERENCE_RE = re.compile(
    r"这款|这块|这料子|这面料|这批|这个|那款|那块|那料子|那面料|那批|那个|该面料|它"
)
_GENUINE_QUESTION_RE = re.compile(GENUINE_QUESTION_PATTERN)
_DISCOUNT_RE = re.compile(DISCOUNT_INDUCEMENT_PATTERN)
_SELF_NARRATION_RE = re.compile(SELF_NARRATION_PATTERN)
_USAGE_NOUN_RE = re.compile(USAGE_NOUN_PATTERN)
_THREAD_COUNT_RE = re.compile(r"(\d+)支")
_PREFERENCE_ONLY_RE = re.compile(
    r"^(?:我|我们)?(?:更喜欢|比较喜欢|喜欢|偏爱|更倾向|更看重).+$"
)
_EXPLICIT_FACT_CUE_RE = re.compile(
    r"(?:这款|这个面料|这块布|成分是|成分为|含有|库存|现货|价格|售价|单价|"
    r"缩水率|效果很好|性能|幅宽|门幅|颜色是|色号是|是纯棉|为纯棉|"
    r"\d+(?:\.\d+)?\s*[%％])"
)
_OBJECTIVE_FACT_PATTERNS: tuple[tuple[str, str], ...] = (
    (
        "composition",
        r"(?:(?:成分|材质|含量|比例|占比)(?:是|为|有|含有?)?.{0,12}"
        r"(?:纯棉|棉麻|涤纶|羊毛|真丝|亚麻|锦纶|粘纤|氨纶|\d+(?:\.\d+)?\s*[%％])"
        r"|(?:是|为|含有?|包含).{0,5}(?:纯棉|棉麻|涤纶|羊毛|真丝|亚麻|锦纶|粘纤|氨纶)"
        r"|(?:这款|这个面料|这块布|面料)(?:是|为|的)?(?:纯棉|棉麻|涤纶|羊毛|真丝|亚麻|锦纶|粘纤|氨纶)"
        r"|(?:纯棉|棉麻|涤纶|羊毛|真丝|亚麻|锦纶|粘纤|氨纶).{0,5}\d+(?:\.\d+)?\s*[%％])",
    ),
    (
        "inventory_status",
        r"(?:库存|现货|存货)(?:是|为|有|还剩)?(?:充足|充裕|很多|足够|有货|没货|不足|不多|售罄|卖完)",
    ),
    (
        "price",
        r"(?:价格|售价|单价|米价|一米)(?:是|为)?\s*\d+(?:\.\d+)?\s*(?:元|块)"
        r"|\d+(?:\.\d+)?\s*(?:元|块)(?:一米|每米)",
    ),
    ("shrinkage_rate", r"(?:缩水率|缩水)(?:是|为)?\s*\d+(?:\.\d+)?\s*[%％]"),
    (
        "product_effect",
        r"(?:效果|性能)(?:特别|非常|很|挺|比较)?(?:好|不错|优秀|明显|强|差|高|低)",
    ),
    (
        "breathability",
        r"(?:这款|这个面料|这块布|面料)(?:特别|非常|很|挺|比较)?透气(?:性)?"
        r"(?:特别|非常|很|挺|比较)?(?:好|强|不错|差|一般)?"
        r"|(?:特别|非常|很|挺|比较|不)?透气(?:性)?(?:特别|非常|很|挺|比较)?"
        r"(?:好|强|不错|差|一般)|不闷",
    ),
    (
        "fabric_attribute",
        r"(?:这款|这个面料|这块布|面料)(?:特别|非常|很|挺|比较)?"
        r"(?:柔软|亲肤|防水|防皱|耐磨|有垂感|有弹力|不易起球)",
    ),
    (
        "width",
        r"(?:门幅|幅宽|宽度)(?:是|为)?\s*\d+(?:\.\d+)?\s*(?:厘米|毫米|公分|米|cm|mm)",
    ),
    ("color", r"(?:颜色|色号)(?:是|为)?[黑白红蓝棕紫深浅绿黄灰橙粉米咖银金]+色"),
)
_OBJECTIVE_FACT_RE = tuple(
    (predicate, re.compile(pattern)) for predicate, pattern in _OBJECTIVE_FACT_PATTERNS
)
_METER_DIGIT_RE = re.compile(r"(?<!\d)(\d+(?:\.\d+)?)米(半)?")
_METER_CHINESE_RE = re.compile(r"([零〇一二两三四五六七八九十百千]+)米(半)?")
_CHINESE_DIGITS = {
    "零": 0,
    "〇": 0,
    "一": 1,
    "二": 2,
    "两": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
}
_CHINESE_UNITS = {"十": 10, "百": 100, "千": 1000}


def _parse_chinese_number(value: str) -> int:
    """把 ``十`` / ``两`` / ``一百`` 这类中文数字转成整数。

    标准算法:数字先记在手上,遇到单位才结算一次(``十`` 独自出现按 ``一十`` 处理)。
    遇到解析不了的字直接放弃,返回 0 —— 0 不会被当成"超限",所以解析失败的方向是
    **不拒绝**,由其它更明确的规则兜底。
    """

    section = 0
    number = 0
    for char in value:
        if char in _CHINESE_DIGITS:
            number = _CHINESE_DIGITS[char]
            continue
        unit = _CHINESE_UNITS.get(char)
        if unit is None:
            return 0
        section += (number or 1) * unit
        number = 0
    return section + number


def concrete_meter_amounts(text: str) -> tuple[float, ...]:
    """抽出文本里明确说出的米数(含中文数字与"半")。

    与旧校验器逐字一致:阿拉伯数字、中文数字各扫一遍,``半米`` 单独补一条。
    """

    amounts: list[float] = []
    for value, half in _METER_DIGIT_RE.findall(text):
        amounts.append(float(value) + (0.5 if half else 0.0))
    for value, half in _METER_CHINESE_RE.findall(text):
        amounts.append(float(_parse_chinese_number(value)) + (0.5 if half else 0.0))
    if "半米" in text:
        amounts.append(0.5)
    return tuple(amounts)


@dataclass(frozen=True, slots=True)
class BuyerClothRules:
    """当前版本的全部规则数据。

    evaluator 与 prompt 投影都只读这一份:**prompt 与 validator 来自同一份数据**,
    否则"模型按 A 生成、被 B 拒绝"会让 AI 一直不发言,而日志里查不出原因。
    """

    max_meter_amount: float = 6.0
    max_thread_count: int = 60
    disabled_dimensions: frozenset[AttributeDimension] = frozenset(
        {AttributeDimension.WEIGHT}
    )
    lace_quota: RollingQuota = RollingQuota(tag="lace", window_size=50, max_count=3)
    rare_unanchored_quota: RollingQuota = RollingQuota(
        tag="usage_priority:rare_unanchored", window_size=20, max_count=2
    )
    rare_consecutive_quota: RollingQuota = RollingQuota(
        tag="usage_priority:rare_unanchored", window_size=2, max_count=1
    )

    @property
    def rolling_content_policy(self) -> RollingContentPolicy:
        return RollingContentPolicy(
            (self.lace_quota, self.rare_unanchored_quota, self.rare_consecutive_quota)
        )


#: 本地规则数据。版本升级意味着**显式评审并改这里的常量**,而不是让外部仓库
#: 的改动自动影响主项目。
BUYER_CLOTH_RULES_V1 = BuyerClothRules()


class FabricBuyerPolicy:
    """布料零售内容策略:确定性判定,不调用模型、不看时间、不读网络。

    判定顺序(稳定契约,回归语料依赖它):

    1. 空文本;
    2. 引导降价(它比词表更具体:便宜/优惠/赠品同属两类,顺序决定拒绝码);
    3. 禁用词表(销售/生活、质量风险、情绪表演、窄风格词、营销色名);
    4. 禁用属性维度(重量);
    5. 承诺/成交动词;
    6. 混合选择等错误句式;
    7. 句族判据(决策方法、开放性问题、主观感受、织法、元问句、笼统行业词、流程叙述);
    8. 纯自述弹幕;
    9. 米数上限,以及"具体米数必须提问";
    10. 支数上限;
    11. 宽泛夸赞必须接选购问题;
    12. "这个/这款"客观属性只能提问;
    13. 用途 × 属性兼容。

    与旧仓库的差别:旧实现把"生成前过滤器"和"生成后校验器"分在两处,同一条候选可能
    先被过滤器静默丢弃、再由校验器抛出;这里合成一条**有序**判定链,因此拒绝原因是
    确定的——诊断能回答"为什么这条被拒",而不是"它没进语料"。
    """

    def __init__(self, rules: BuyerClothRules = BUYER_CLOTH_RULES_V1) -> None:
        self._rules = rules
        self._patterns = tuple(
            (reason, re.compile(pattern)) for reason, pattern in PATTERN_RULES
        )
        self.rolling_content_policy = rules.rolling_content_policy

    @property
    def policy_id(self) -> str:
        return BUYER_CLOTH_POLICY_ID

    @property
    def version(self) -> int:
        return BUYER_CLOTH_POLICY_VERSION

    @property
    def display_name(self) -> str:
        # 展示名是 pack 元数据,不是规则:界面通过 registry 的 descriptors 读它。
        return "布料零售"

    @property
    def trusted_fact_source(self) -> TrustedFactSource | None:
        """No catalog/source is wired into the current product runtime."""

        return None

    def objective_fact_claims(self, candidate: str) -> tuple[ObjectiveFactClaim, ...]:
        """Classify factual assertions; preferences and questions are not claims."""

        text = str(candidate or "").strip()
        if not text:
            return ()
        claims: list[ObjectiveFactClaim] = []
        seen: set[tuple[str, str]] = set()
        clauses = re.split(r"(?<=[，,。；;！？?!])", text)
        for clause in clauses:
            if (
                BUYER_CLOTH_PARTICIPATION_INTERPRETER.resolve_participation_act(
                    clause, None
                )
                == "question"
            ):
                continue
            if (
                _PREFERENCE_ONLY_RE.fullmatch(clause.strip()) is not None
                and _EXPLICIT_FACT_CUE_RE.search(clause) is None
            ):
                continue
            for predicate, pattern in _OBJECTIVE_FACT_RE:
                match = pattern.search(clause)
                if match is None:
                    continue
                value = match.group(0).strip()
                key = (predicate, value)
                if key in seen:
                    continue
                seen.add(key)
                claims.append(
                    ObjectiveFactClaim.from_candidate(
                        text,
                        subject="active_product",
                        predicate=predicate,
                        value=value,
                    )
                )
        return tuple(claims)

    @property
    def rules(self) -> BuyerClothRules:
        return self._rules

    @property
    def viewer_archetypes(self) -> tuple[ViewerArchetype, ...]:
        """Stable viewer interests, separate from industry usage priority."""

        return BUYER_CLOTH_VIEWER_ARCHETYPES

    def viewer_topic_tags(self, text: str) -> tuple[str, ...]:
        """Classify explicit chat anchors using this pack's topic vocabulary."""

        return buyer_cloth_viewer_topic_tags(text)

    @property
    def participation_interpreter(self) -> ParticipationPolicyInterpreter:
        """Expose this pack's deterministic participation interpretation rules."""

        return BUYER_CLOTH_PARTICIPATION_INTERPRETER

    # ---------- 生成前 ----------

    def project_prompt(
        self,
        *,
        phase: ContextPhase,
        bootstrap: BootstrapContext,
        user_topic: str = "",
    ) -> PromptPolicyProjection:
        """按阶段投影生成偏好。

        阶段不同,允许说的话不同:Cold Start 还没有任何真实聊天,只允许与未观察事实
        无关的表达;进入 Contextual 之后才可以承接正在发生的话题。**它只是偏好**——
        真正的许可判据是 :meth:`evaluate`。
        """

        notes: tuple[str, ...]
        intents: tuple[str, ...]
        if phase is ContextPhase.COLD_START:
            notes = (NOTE_COLD_START_SAFE, NOTE_NO_FACT_CLAIM, NOTE_MIX_GUIDANCE)
            intents = ("topic_question", "usage_question", "parameter_question")
        elif phase is ContextPhase.WARMING:
            notes = (NOTE_ASK_NOT_ASSERT, NOTE_GROUNDED)
            intents = ("topic_follow_up", "parameter_question", "usage_question")
        else:
            notes = (NOTE_GROUNDED, NOTE_ASK_NOT_ASSERT)
            intents = ("topic_follow_up", "parameter_question", "usage_question")
        return PromptPolicyProjection(
            policy_id=self.policy_id,
            version=self.version,
            preferred_intents=intents,
            forbidden_dimensions=tuple(
                sorted(dimension.value for dimension in self._rules.disabled_dimensions)
            ),
            phase_notes=notes,
            hard_constraints=(
                "布料直播间卖的是布料，不是成衣；不询问成衣版型、衣服尺码、偏大偏小、"
                "宽松或修身、成衣合身度和衣服围度尺寸、上身效果或穿搭，也不讨论搭配裤子或裙子。"
                "可以讨论布料本身及它能做什么。",
                "有观众弹幕时优先结合最近50条观众弹幕，最近10条权重最高，自然承接当前话题。"
                "冷启动时根据本场明示主题或布料用途，提出一个对买家有实际帮助的具体问题；"
                "不要只问候、报到、蹲守、空问今天聊什么，或提出选购方法考题。"
                "不要跳到无关商品属性；没有具体有用的问题时才返回空候选。",
                "不要把聊天中没有出现的面料成分、厚薄、颜色、用途或商品状态当成事实。",
                "用途优先听最近观众弹幕，其次是本场明示主题；若均未明确，常见提问约七成围绕"
                "发圈、连衣裙、裤子、衬衫、半身裙、外套、包包，两成围绕上衣、睡衣、"
                "家居服等其他常见衣物，一成才偶尔涉及围裙、窗帘、桌布、抱枕套、"
                "坐垫、收纳袋、玩偶等低频用途。低频用途不要连续出现；观众明确聊到时"
                "自然承接，不受默认分布限制。",
                "不要主动提缩水、会不会缩、洗了会缩、下水会缩等质量风险；"
                "同一条只问一件事，先承接观众话题，不拼接无关用途。",
            ),
        )

    # ---------- 生成后 ----------

    def evaluate(self, candidate: str) -> PolicyDecision:
        text = str(candidate or "").strip()
        if not text:
            return PolicyDecision.reject(REASON_EMPTY)
        rejection = self._first_rejection(text)
        if rejection is not None:
            return PolicyDecision.reject(rejection, *self.tags_for(text))
        return PolicyDecision.accept(*self.tags_for(text))

    def evaluate_with_context(
        self, candidate: str, *, recent_chat: tuple[str, ...], user_topic: str
    ) -> PolicyDecision:
        """明确话题优先；只有缺少当前话题锚点的低频用途计入兜底配额。"""

        decision = self.evaluate(candidate)
        if not decision.allowed:
            return decision
        if (
            "发圈" in candidate
            and "透气" in candidate
            and not any(
                "发圈" in message and "透气" in message for message in recent_chat[-10:]
            )
        ):
            return PolicyDecision.reject(REASON_USAGE_ATTRIBUTE)
        if _DANGLING_REFERENCE_RE.search(candidate) is not None:
            candidate_topics = set(buyer_cloth_viewer_topic_tags(candidate))
            anchor_topics = {
                topic
                for message in recent_chat[-10:]
                for topic in buyer_cloth_viewer_topic_tags(message)
            }
            anchor_topics.update(buyer_cloth_viewer_topic_tags(user_topic))
            if not candidate_topics & anchor_topics:
                return PolicyDecision.reject(REASON_UNGROUNDED_REFERENCE)
        if priority_for(candidate) is not UsagePriority.RARE:
            return decision
        candidate_topics = {topic.name for topic in topics_in(candidate)}
        recent_topics = {
            topic.name for message in recent_chat[-5:] for topic in topics_in(message)
        }
        anchor_topics = recent_topics or {topic.name for topic in topics_in(user_topic)}
        if candidate_topics & anchor_topics:
            return decision
        return PolicyDecision.accept(*decision.tags, "usage_priority:rare_unanchored")

    def _first_rejection(self, text: str) -> str | None:
        rules = self._rules
        # 引导降价先判:它比"销售/生活词表"更具体,而且诊断价值更高——用户想知道
        # 的是"这条在议价",而不是"它命中了某个词"。词表里那几个词(便宜/优惠/
        # 赠品)同时属于两类,所以顺序决定了拒绝码。
        if _DISCOUNT_RE.search(text) is not None:
            return REASON_DISCOUNT
        for reason, terms in _BANKS:
            if any(term in text for term in terms):
                return reason
        for dimension, terms in DISABLED_DIMENSION_TERMS:
            if dimension in rules.disabled_dimensions and any(
                term in text for term in terms
            ):
                return REASON_DISABLED_DIMENSION
        if any(term in text for term in COMMITMENT_TERMS):
            return REASON_COMMITMENT
        if any(term in text for term in MIXED_SELECTION_TERMS):
            return REASON_MIXED_SELECTION
        for reason, pattern in self._patterns:
            if pattern.search(text) is not None:
                return reason
        if self._is_self_narration(text):
            return REASON_SELF_NARRATION
        amounts = concrete_meter_amounts(text)
        if any(amount > rules.max_meter_amount for amount in amounts):
            return REASON_METER_OVER_LIMIT
        asks = _GENUINE_QUESTION_RE.search(text) is not None
        if amounts and not asks:
            # 与旧校验器一致:具体米数只能出现在询问里。旧测试里那条更宽松的
            # "数量问句"正则**没有**被采纳(见模块 docstring 第 2 点)。
            return REASON_METER_STATEMENT
        if any(
            int(value) > rules.max_thread_count
            for value in _THREAD_COUNT_RE.findall(text)
        ):
            return REASON_THREAD_OVER_LIMIT
        if any(term in text for term in PRAISE_TERMS) and not (
            _BUYING_TOPIC_RE.search(text) is not None and asks
        ):
            return REASON_PRAISE_WITHOUT_QUESTION
        if (
            text.startswith(("这个", "这款"))
            and _OBJECTIVE_TOPIC_RE.search(text) is not None
            and not asks
        ):
            return REASON_OBJECTIVE_CLAIM
        return self._usage_attribute_rejection(text)

    @staticmethod
    def _is_self_narration(text: str) -> bool:
        """纯自述:开头是"准备/想先…",又没有真问题、也没有具体用途。"""

        if _SELF_NARRATION_RE.search(text) is None:
            return False
        if _GENUINE_QUESTION_RE.search(text) is not None:
            return False
        return _USAGE_NOUN_RE.search(text) is None

    @staticmethod
    def _usage_attribute_rejection(text: str) -> str | None:
        if any(usage in text for usage in HOME_USAGES) and any(
            term in text for term in HOME_FORBIDDEN_ATTRIBUTES
        ):
            return REASON_USAGE_ATTRIBUTE
        if any(usage in text for usage in CRAFT_USAGES) and any(
            term in text for term in CRAFT_FORBIDDEN_ATTRIBUTES
        ):
            return REASON_USAGE_ATTRIBUTE
        for usage, attribute in USAGE_ATTRIBUTE_CONFLICTS:
            if usage in text and attribute in text:
                return REASON_USAGE_ATTRIBUTE
        return None

    # ---------- 标签 ----------

    def tags_for(self, text: str) -> tuple[str, ...]:
        """给候选打标签,供滚动配额与诊断使用。

        ``lace`` 和缺乏话题锚点的低频用途受配额约束。旧用途组
        (garment/home/craft/special)与新优先级并存，含义彼此独立。
        """

        value = str(text or "")
        tags: list[str] = []
        if any(term in value for term in LACE_TERMS):
            tags.append("lace")
        tags.append(self.usage_group_for(value))
        priority = priority_for(value)
        if priority is not None:
            tags.append(f"usage_priority:{priority.value}")
        attributes = {
            "dimensions",
            "fabric_width",
            "fabric_drape",
            "stretch",
            "yardage",
            "composition",
            "softness",
            "breathability",
            "color",
            "pattern",
            "current_item",
        }
        tags.extend(
            f"attribute:{tag}"
            for tag in buyer_cloth_viewer_topic_tags(value)
            if tag in attributes
        )
        tags.extend(f"usage:{topic.name}" for topic in topics_in(value))
        return tuple(tags)

    @staticmethod
    def usage_group_for(text: str) -> str:
        """返回用途组;旧仓库的测试要求"一条只属于一个组"。

        判定顺序:特殊话题优先(童装/宠物不进通用池),然后成衣、家用、手工;
        都没有时归 ``general``。
        """

        if any(marker in text for marker in SPECIAL_MARKERS):
            return "special"
        if any(usage in text for usage in GARMENT_USAGES):
            return "garment"
        if any(usage in text for usage in HOME_USAGES):
            return "home"
        if any(usage in text for usage in CRAFT_USAGES):
            return "craft"
        return "general"


__all__ = [
    "AttributeDimension",
    "BUYER_CLOTH_POLICY_ID",
    "BUYER_CLOTH_POLICY_VERSION",
    "BUYER_CLOTH_RULES_V1",
    "FabricBuyerPolicy",
    "BuyerClothRules",
    "REASON_FINISHED_GARMENT_TOPIC",
    "REASON_UNGROUNDED_REFERENCE",
    "GARMENT_USAGES",
    "HOME_USAGES",
    "CRAFT_USAGES",
    "LACE_TERMS",
    "SPECIAL_MARKERS",
    "concrete_meter_amounts",
]
