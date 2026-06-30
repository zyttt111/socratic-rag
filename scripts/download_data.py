"""一键下载哲学原著。

从 Project Gutenberg 等公开源下载。
默认 10 本经典。
"""

import sys
from pathlib import Path

import httpx
from loguru import logger
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)

# 默认 10 本经典（Project Gutenberg + 中文译本）
DEFAULT_BOOKS = {
    # 英文经典
    "plato-republic": {
        "url": "https://www.gutenberg.org/cache/epub/150/pg150.txt",
        "title": "理想国（英译）",
        "philosopher": "柏拉图",
    },
    "aristotle-ethics": {
        "url": "https://www.gutenberg.org/cache/epub/8438/pg8438.txt",
        "title": "尼各马可伦理学（英译）",
        "philosopher": "亚里士多德",
    },
    "descartes-meditations": {
        "url": "https://www.gutenberg.org/cache/epub/23306/pg23306.txt",
        "title": "第一哲学沉思集（英译）",
        "philosopher": "笛卡尔",
    },
    "nietzsche-zara": {
        "url": "https://www.gutenberg.org/cache/epub/1998/pg1998.txt",
        "title": "查拉图斯特拉如是说（英译）",
        "philosopher": "尼采",
    },
    # 中译本（用户可手动添加 URL）
    # "kant-krv": {
    #     "url": "https://example.com/kant-krv-zh.txt",
    #     "title": "纯粹理性批判（韦卓民译）",
    #     "philosopher": "康德",
    # },
}


def download_all(
    output_dir: str = "data/raw",
    books: dict | None = None,
) -> int:
    """下载所有书籍。

    Args:
        output_dir: 输出目录
        books: 书籍字典（默认 DEFAULT_BOOKS）

    Returns:
        下载成功数量
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    books = books or DEFAULT_BOOKS

    success = 0
    with Progress(
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        DownloadColumn(),
        TransferSpeedColumn(),
        TimeRemainingColumn(),
    ) as progress:
        for book_id, book_info in books.items():
            task = progress.add_task(
                f"下载 {book_info['title']}",
                total=None,
            )

            target = output_dir / f"{book_id}.txt"
            if target.exists():
                progress.update(task, completed=100, total=100)
                logger.info(f"  ✓ 已存在: {target.name}")
                continue

            try:
                with httpx.stream("GET", book_info["url"], timeout=30, follow_redirects=True) as response:
                    response.raise_for_status()
                    total = int(response.headers.get("content-length", 0))
                    progress.update(task, total=total)

                    with open(target, "wb") as f:
                        for chunk in response.iter_bytes(chunk_size=8192):
                            f.write(chunk)
                            progress.update(task, advance=len(chunk))

                success += 1
                logger.info(f"  ✓ 下载完成: {target.name}")

            except Exception as e:
                logger.error(f"  ✗ 下载失败: {book_info['title']} - {e}")
                if target.exists():
                    target.unlink()

    logger.info(f"\n✓ 共下载 {success}/{len(books)} 本书")
    logger.info(f"  路径: {output_dir.absolute()}")
    logger.info("\n💡 中文译本需要手动获取：")
    logger.info("   - 汉译世界学术名著丛书：https://www.cp.com.cn/")
    logger.info("   - 下载后放到 data/raw/ 目录，命名为 {philosopher}-{book}.txt")

    return success


def main():
    """CLI 入口"""
    import argparse

    parser = argparse.ArgumentParser(description="下载哲学原著")
    parser.add_argument(
        "--output",
        "-o",
        default="data/raw",
        help="输出目录（默认 data/raw）",
    )
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("📚 哲学原著下载工具")
    logger.info("=" * 60)

    success = download_all(args.output)

    if success == 0:
        logger.error("所有下载都失败了，请检查网络")
        sys.exit(1)


if __name__ == "__main__":
    main()