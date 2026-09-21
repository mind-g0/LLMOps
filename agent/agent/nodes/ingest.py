"""Ingest node: any CV file (PDF / image / DOCX / txt / md / json) -> page images + text layer.

Docling first (cheap, CPU) for a text layer; page images are always prepared so the VLM can take over
when the text layer is missing or fails validation.
"""
import hashlib
import json
from functools import lru_cache
import shutil
import subprocess
from pathlib import Path

from agent.logger import get_logger, log_node
from agent.state import HRState, RDEMError
from config import settings as S
from utils.text import alnum_ratio, presentation_form_ratio

_IMG = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}
_TXT = {".txt", ".md", ".json"}


def text_is_usable(text: str) -> bool:
    """Router check from the plan: near-empty, noisy, or garbled-Arabic text layers escalate to vision."""
    return (
        len(text.strip()) >= S.MIN_TEXT_CHARS
        and alnum_ratio(text) >= S.MIN_ALNUM_RATIO
        and presentation_form_ratio(text) <= S.MAX_PRESENTATION_FORM_RATIO
    )


def _resize(img):
    w, h = img.size
    scale = S.PAGE_MAX_SIDE / max(w, h)
    return img.resize((int(w * scale), int(h * scale))) if scale < 1 else img


def _render_pdf(path: Path, out_dir: Path) -> tuple[list[str], str]:
    import pypdfium2 as pdfium  # lazy

    pdf = pdfium.PdfDocument(str(path))
    paths, texts = [], []
    for i in range(min(len(pdf), S.MAX_PAGES)):
        page = pdf[i]
        img = _resize(page.render(scale=S.PAGE_RENDER_SCALE).to_pil().convert("RGB"))
        p = out_dir / f"page_{i + 1}.png"
        img.save(p)
        paths.append(str(p))
        texts.append(page.get_textpage().get_text_range())
    return paths, "\n".join(texts)


@lru_cache(maxsize=1)
def _converter():
    """One converter per process (building it loads models). Mode comes from DOCLING_MODE.

    Why not the library default: it runs Docling's OCR on scanned pages. That OCR text can look
    'usable' to text_is_usable() (long enough, alphanumeric) while being wrong, especially for
    Arabic, and then the VLM would never be asked. With OCR off, a scan yields no text and the
    router escalates to the VLM, which is the design.
    """
    from docling.datamodel.base_models import InputFormat  # lazy, heavy
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption

    mode = S.DOCLING_MODE
    if mode == "full":
        return DocumentConverter()
    opts = PdfPipelineOptions(do_ocr=False, do_table_structure=(mode == "tables"))
    return DocumentConverter(format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=opts)})


def _docling_text(path: Path) -> str:
    try:
        return _converter().convert(str(path)).document.export_to_markdown()
    except Exception as e:
        get_logger().debug(f"    docling unavailable/failed ({type(e).__name__}); using fallback")
        return ""


def _docx_text_fallback(path: Path) -> str:
    """Pure-python text for .docx (paragraphs + table cells) when Docling is unavailable."""
    try:
        from docx import Document  # python-docx (already a Docling dependency)

        doc = Document(str(path))
        parts = [p.text for p in doc.paragraphs if p.text.strip()]
        for table in doc.tables:
            for row in table.rows:
                parts.append(" | ".join(c.text.strip() for c in row.cells if c.text.strip()))
        return "\n".join(parts)
    except Exception as e:
        get_logger().debug(f"    python-docx fallback failed ({type(e).__name__})")
        return ""


def _office_to_pdf(path: Path, out_dir: Path) -> Path | None:
    """Word -> PDF with headless LibreOffice, so the VLM can SEE the layout when the text path fails.

    A private profile dir per conversion is required: LibreOffice locks its default profile, so two
    parallel conversions would otherwise fail or hang.
    """
    exe = shutil.which("soffice") or shutil.which("libreoffice")
    if not exe:
        get_logger().info("  [ingest] LibreOffice not installed: Word file will use the text layer only")
        return None
    profile = out_dir / "lo_profile"
    try:
        subprocess.run(
            [exe, f"-env:UserInstallation=file://{profile.resolve()}", "--headless", "--convert-to", "pdf",
             "--outdir", str(out_dir), str(path)],
            check=True, capture_output=True, timeout=120)
    except Exception as e:
        get_logger().warning(f"  [ingest] Word->PDF conversion failed: {type(e).__name__}: {str(e)[:200]}")
        return None
    pdf = out_dir / f"{path.stem}.pdf"
    return pdf if pdf.exists() else None


@log_node
def ingest(state: HRState) -> dict:
    path = Path(state.cv_path)
    if not path.is_file():
        rdem = RDEMError(node="ingest", error_type="file_not_found", message=f"{path} does not exist")
        return {"status": "failed", "global_error_log": [rdem], "_status": "error"}

    cid = hashlib.sha1(path.read_bytes()).hexdigest()[:10]
    out_dir = S.TMP_DIR / cid
    out_dir.mkdir(parents=True, exist_ok=True)
    ext = path.suffix.lower()
    pages: list[str] = []
    text = ""

    try:
        if ext in _TXT:
            raw = path.read_text(encoding="utf-8")
            text = json.dumps(json.loads(raw), ensure_ascii=False) if ext == ".json" else raw
        elif ext in _IMG:
            from PIL import Image

            p = out_dir / "page_1.png"
            _resize(Image.open(path).convert("RGB")).save(p)
            pages = [str(p)]
        elif ext == ".pdf":
            pages, layer = _render_pdf(path, out_dir)
            text = _docling_text(path) or layer
        elif ext in {".docx", ".doc"}:
            # text from the DOCX itself is exact (no OCR/extraction noise), so it is preferred
            text = _docling_text(path) or (_docx_text_fallback(path) if ext == ".docx" else "")
            pdf = _office_to_pdf(path, out_dir)
            if pdf:
                pages, layer = _render_pdf(pdf, out_dir)
                text = text or layer
        else:
            raise ValueError(f"unsupported file type '{ext}'")
    except Exception as e:
        rdem = RDEMError(node="ingest", error_type="ingest_failed", message=f"{type(e).__name__}: {e}",
                         suggestion="Check the file is a valid, non-encrypted CV.")
        return {"status": "failed", "global_error_log": [rdem], "_status": "error"}

    if not pages and not text.strip():
        rdem = RDEMError(node="ingest", error_type="empty_document", message="No text or page images could be produced.")
        return {"status": "failed", "global_error_log": [rdem], "_status": "error"}

    ok = text_is_usable(text)
    get_logger().info(f"  [ingest] id={cid} pages={len(pages)} text_chars={len(text)} text_ok={ok}")
    return {"candidate_id": cid, "page_paths": pages, "text_layer": text, "text_ok": ok}
