"""文档加载器。

支持：
- .txt（纯文本，Project Gutenberg / 商业电子书）
- .pdf（PDF，PyPDFLoader 主力 + MinerU 扫描版回退）
- .md（Markdown）
- 整个目录
"""

from pathlib import Path
from typing import List, Optional

from langchain_core.documents import Document
from langchain_community.document_loaders import (
    DirectoryLoader,
    PyPDFLoader,
    TextLoader,
    UnstructuredMarkdownLoader,
)
from loguru import logger

# 可检测字符（包含 CJK 的 PDF text 层正常会解析出这些）
_READABLE_CHARS = set(
    "的一是在不了有和人这中大为上个国我以要他时来用们生到作地于出就分对成会可主发年动同工也能下过子说产种面而方后多定行学法所民得经十三之进着等部度家电力里如水化高自二理起小物现实加量都两体制机当使点从业本去把性好应开它合还因由其些然前外天政四日那社义事平形相全表间样与关各重新线内数正心反你明看原又么利比或但质气第向道命此变条只没结解问意建月公无系军很情者最立代想已通并提直题党程展五果料象员革位入常文总次品式活设及管特件长求老头基资边流路级少图山统接知较将组见计别她手角期根论运农指几九区强放决西被干做必战先回则任取据处队南给色光门即保治北造百规热领七海口东导器压志世金增争济阶油思术极交受联什认六共权收证改清己美再采转更单风切打白教速花带安场身车例真务具万每目至达走积示议声报斗完类八离华名确才科张信马节话米整空元况今集温传土许步群广石记需段研界拉林律叫且究观越织装影算低持音众书布复容儿须际商非验连断深难近矿千周委素技备半办青省列习响约支般史感劳便团往酸历市克何除消构府称太准精值号率族维划选标写存候毛亲快效斯院查江型眼王按格养易置派层片始却专状育厂京识适属圆包火住调满县局照参红细引听该铁价严龙飞"
)


def _is_garbled(text: str, sample_size: int = 1000) -> bool:
    """检测 PDF 提取文本是否乱码（无文本层时 PyPDFLoader 返回空串或乱码）。

    启发式：对前 sample_size 字统计可读字符占比，低于阈值视为乱码。
    """
    sample = text[:sample_size]
    if not sample.strip():
        return True
    readable = sum(1 for c in sample if c in _READABLE_CHARS)
    ratio = readable / len(sample)
    return ratio < 0.15


def load_pdf(file_path: Path) -> List[Document]:
    """加载 PDF（PyPDFLoader 主力，轻量快速）。

    对文本层 PDF（商务印书馆电子版等）效果最佳。
    扫描版 PDF 返回的 Document 中 page_content 可能为空或乱码，
    此时可调用 load_pdf_with_mineru() 作为回退。
    """
    loader = PyPDFLoader(str(file_path))
    documents = loader.load()
    # 标记来源
    for doc in documents:
        doc.metadata["source"] = str(file_path)
        doc.metadata["loader"] = "pypdf"
    logger.info(f"  ✓ 加载 {len(documents)} 页 (PyPDF)")
    return documents


def load_pdf_with_mineru(
    pdf_path: str | Path,
    parse_method: str = "auto",
) -> List[Document]:
    """使用 MinerU 解析 PDF（高质量，适合扫描版 / 含图表公式的学术 PDF）。

    MinerU 需要 ~/.magic-pdf.json 配置文件。
    首次使用前请创建（参考 https://github.com/opendatalab/MinerU）：

        cat > ~/.magic-pdf.json << 'EOF'
        {
          "bucket_info": {
            "bucket-name-1": ["ak", "sk", "endpoint"],
            "bucket-name-2": ["ak", "sk", "endpoint"]
          },
          "models-dir": "/tmp/mineru-models",
          "device-mode": "cpu",
          "table-config": {},
          "layout-config": {}
        }
        EOF

    Args:
        pdf_path: PDF 文件路径
        parse_method: "auto" / "txt" / "ocr"

    Returns:
        Document 列表（每页一个 Document，page_content 为 Markdown）
    """
    import tempfile
    from pathlib import Path

    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF 文件不存在: {pdf_path}")

    pdf_bytes = pdf_path.read_bytes()

    try:
        from magic_pdf.data.data_reader_writer import FileBasedDataWriter
        from magic_pdf.data.dataset import PymuDocDataset
        from magic_pdf.model.doc_analyze_by_custom_model import doc_analyze
        from magic_pdf.config.enums import SupportedPdfParseMethod
    except ImportError:
        raise ImportError(
            "MinerU 未安装，请运行: uv sync (magic-pdf 已在 pyproject.toml 依赖中)"
        )
    except FileNotFoundError as e:
        raise FileNotFoundError(
            f"Missing MinerU config: {e}\n"
            "请创建 ~/.magic-pdf.json，参考 https://github.com/opendatalab/MinerU"
        )

    with tempfile.TemporaryDirectory(prefix="mineru-") as tmpdir:
        image_dir = Path(tmpdir) / "images"
        image_dir.mkdir(exist_ok=True)

        image_writer = FileBasedDataWriter(str(image_dir))
        md_writer = FileBasedDataWriter(str(tmpdir))

        ds = PymuDocDataset(pdf_bytes)
        method = ds.classify() if parse_method == "auto" else (
            SupportedPdfParseMethod.TXT if parse_method == "txt"
            else SupportedPdfParseMethod.OCR
        )
        logger.info(f"  MinerU parse method: {method}")

        ocr = method == SupportedPdfParseMethod.OCR
        infer_result = ds.apply(doc_analyze, ocr=ocr)

        if ocr:
            pipe_result = infer_result.pipe_ocr_mode(image_writer, debug_mode=False)
        else:
            pipe_result = infer_result.pipe_txt_mode(image_writer, debug_mode=False)

        pipe_result.dump_md(md_writer, f"{pdf_path.stem}.md", str(image_dir.name))

        md_path = Path(tmpdir) / f"{pdf_path.stem}.md"
        markdown_text = md_path.read_text(encoding="utf-8")

    return [Document(
        page_content=markdown_text,
        metadata={"source": str(pdf_path), "loader": "mineru", "parse_method": str(method)},
    )]


def load_book(file_path: str | Path) -> List[Document]:
    """加载单个文件。

    支持 .txt / .md / .pdf。
    PDF 优先使用 PyPDFLoader（快速），扫描版建议使用 load_pdf_with_mineru()。

    Args:
        file_path: 文件路径

    Returns:
        Document 列表
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")

    suffix = file_path.suffix.lower()
    logger.info(f"加载文件: {file_path} (类型: {suffix})")

    if suffix == ".pdf":
        documents = load_pdf(file_path)
        # 检测是否扫描版（无文本层）
        sample = "\n".join(d.page_content for d in documents[:3])
        if _is_garbled(sample):
            logger.warning(
                "⚠ PDF 可能为扫描版（文本层缺失或乱码），"
                "建议改用 load_pdf_with_mineru()"
            )
    elif suffix == ".md":
        loader = UnstructuredMarkdownLoader(str(file_path))
        documents = loader.load()
    elif suffix in [".txt", ".text"]:
        loader = TextLoader(str(file_path), encoding="utf-8")
        documents = loader.load()
    else:
        loader = TextLoader(str(file_path), encoding="utf-8")
        documents = loader.load()

    logger.info(f"  ✓ 加载 {len(documents)} 个 Document")
    return documents


def load_directory(
    directory: str | Path,
    glob_pattern: str = "**/*.txt",
    recursive: bool = True,
) -> List[Document]:
    """加载整个目录。

    Args:
        directory: 目录路径
        glob_pattern: 文件匹配模式
        recursive: 是否递归

    Returns:
        Document 列表
    """
    directory = Path(directory)
    if not directory.exists():
        raise FileNotFoundError(f"目录不存在: {directory}")

    loader = DirectoryLoader(
        str(directory),
        glob=glob_pattern,
        recursive=recursive,
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"},
        show_progress=True,
    )

    documents = loader.load()
    logger.info(f"✓ 从 {directory} 加载 {len(documents)} 个文件")
    return documents