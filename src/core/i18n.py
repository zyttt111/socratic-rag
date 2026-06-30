"""中英德三语支持。

哲学经典覆盖多种语言：
- 中文：商务印书馆译本
- 英文：Project Gutenberg / Cambridge
- 德文：康德/黑格尔/海德格尔原版

输出也支持三语切换。
"""

from enum import Enum


class Language(str, Enum):
    """支持的语言"""

    ZH = "zh"
    EN = "en"
    DE = "de"


# 语言显示名
LANGUAGE_NAMES = {
    Language.ZH: "中文",
    Language.EN: "English",
    Language.DE: "Deutsch",
}

# 各语言的 Prompt 引导词
LANGUAGE_INSTRUCTIONS = {
    Language.ZH: "请用中文回答，引用文献用中译本书名。",
    Language.EN: "Please answer in English, cite using original English titles.",
    Language.DE: "Bitte antworten Sie auf Deutsch, zitieren Sie mit Originaltiteln.",
}

# 主要哲学家的多语言名
PHILOSOPHER_NAMES = {
    "kant": {
        Language.ZH: "康德",
        Language.EN: "Immanuel Kant",
        Language.DE: "Immanuel Kant",
    },
    "hegel": {
        Language.ZH: "黑格尔",
        Language.EN: "Georg Wilhelm Friedrich Hegel",
        Language.DE: "Georg Wilhelm Friedrich Hegel",
    },
    "plato": {
        Language.ZH: "柏拉图",
        Language.EN: "Plato",
        Language.DE: "Platon",
    },
    "aristotle": {
        Language.ZH: "亚里士多德",
        Language.EN: "Aristotle",
        Language.DE: "Aristoteles",
    },
    "nietzsche": {
        Language.ZH: "尼采",
        Language.EN: "Friedrich Nietzsche",
        Language.DE: "Friedrich Nietzsche",
    },
    "heidegger": {
        Language.ZH: "海德格尔",
        Language.EN: "Martin Heidegger",
        Language.DE: "Martin Heidegger",
    },
    "descartes": {
        Language.ZH: "笛卡尔",
        Language.EN: "René Descartes",
        Language.DE: "René Descartes",
    },
    "sartre": {
        Language.ZH: "萨特",
        Language.EN: "Jean-Paul Sartre",
        Language.DE: "Jean-Paul Sartre",
    },
    "zhuangzi": {
        Language.ZH: "庄子",
        Language.EN: "Zhuangzi",
        Language.DE: "Zhuangzi",
    },
    "socrates": {
        Language.ZH: "苏格拉底",
        Language.EN: "Socrates",
        Language.DE: "Sokrates",
    },
}


def get_philosopher_name(key: str, lang: Language = Language.ZH) -> str:
    """获取哲学家的本地化名"""
    if key in PHILOSOPHER_NAMES:
        return PHILOSOPHER_NAMES[key].get(lang, key)
    return key


def get_language_instruction(lang: Language) -> str:
    """获取语言引导词"""
    return LANGUAGE_INSTRUCTIONS.get(lang, LANGUAGE_INSTRUCTIONS[Language.ZH])