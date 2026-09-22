from io import BytesIO

from pypdf import PdfReader


def extract_pdf_text(content: bytes) -> str:
    reader = PdfReader(BytesIO(content))
    pages = [(page.extract_text() or "").strip() for page in reader.pages]
    text = "\n\n".join(page for page in pages if page)
    if not text:
        raise ValueError("PDF 中没有可提取的文本，暂不支持扫描版图片简历。")
    return text[:50_000]
