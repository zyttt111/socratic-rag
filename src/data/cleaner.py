"""文本清洗。

去除页眉页脚、章节编号、OCR 错误等。
"""

import re

from loguru import logger


def clean_text(text: str) -> str:
    """通用文本清洗。

    Args:
        text: 原始文本

    Returns:
        清洗后的文本
    """
    # 1. 去除页眉页脚（页码、章节标题重复）
    text = re.sub(r"\n\s*-\s*\d+\s*-\s*\n", "\n", text)
    text = re.sub(r"\n\s*\d+\s*\n", "\n", text)

    # 2. 去除多空行
    text = re.sub(r"\n{3,}", "\n\n", text)

    # 3. 去除行首行尾空白
    lines = [line.strip() for line in text.split("\n")]
    text = "\n".join(lines)

    # 4. 统一标点
    text = text.replace("　", " ")  # 全角空格 → 半角
    text = text.replace(""", '"').replace(""", '"')  # 中文引号 → 英文
    text = text.replace("'", "'").replace("'", "'")

    # 5. 去除 Project Gutenberg 的 license 头尾
    text = _strip_gutenberg(text)

    return text.strip()


def _strip_gutenberg(text: str) -> str:
    """去除 Project Gutenberg 的 license 头尾"""
    start_patterns = [
        r"\*\*\* START OF (THE|THIS) PROJECT GUTENBERG.*?\*\*\*",
        r"《?商务印书馆.*?》?",
    ]
    end_patterns = [
        r"\*\*\* END OF (THE|THIS) PROJECT GUTENBERG.*?\*\*\*",
    ]

    for pattern in start_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            text = text[match.end():]
            break

    for pattern in end_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            text = text[: match.start()]
            break

    return text


def fix_ocr_errors(text: str) -> str:
    """修复常见 OCR 错误。"""
    # 形近字修正（哲学文本常见）
    corrections = {
        "己经": "已经",
        "己知": "已知",
        "仑": "仑",  # 占位
        "藉": "借",
        "覆": "复",
    }
    for wrong, right in corrections.items():
        text = text.replace(wrong, right)
    return text


def normalize_whitespace(text: str) -> str:
    """统一空白字符"""
    text = re.sub(r"[ \t]+", " ", text)  # 多空格 → 单空格
    text = re.sub(r"\n\s*\n", "\n\n", text)  # 多空行 → 双空行
    return text.strip()