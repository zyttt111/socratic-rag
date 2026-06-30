"""Prompt 模板。

支持：
- 学术引证 QA
- 苏格拉底反问
- 概念对比
- 5 个哲学家 persona
"""

from pathlib import Path
from typing import Any

import yaml
from loguru import logger

PROMPTS_DIR = Path(__file__).parent


def load_prompt(name: str, language: str = "zh") -> dict[str, str]:
    """加载 Prompt 模板。

    Args:
        name: 模板名（如 "academic_qa", "socrates"）
        language: 语言 (zh/en/de)

    Returns:
        {"system": ..., "user": ...}
    """
    prompt_file = PROMPTS_DIR / f"{name}.yaml"
    if not prompt_file.exists():
        logger.warning(f"Prompt 不存在: {prompt_file}，使用默认模板")
        return _default_prompt()

    with open(prompt_file, encoding="utf-8") as f:
        prompts = yaml.safe_load(f)

    return prompts.get(language, prompts.get("zh", _default_prompt()))


def _default_prompt() -> dict[str, str]:
    """默认 Prompt"""
    return {
        "system": "你是一位哲学助手。",
        "user": "问题：{question}\n\n参考资料：\n{context}\n\n请基于以上资料回答。",
    }


def list_prompts() -> list[str]:
    """列出所有可用的 Prompt"""
    return [p.stem for p in PROMPTS_DIR.glob("*.yaml")]