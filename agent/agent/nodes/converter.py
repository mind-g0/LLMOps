"""Converter node: any CV file (PDF / image / DOCX / txt / md / json) -> page images.

Text parsing is NOT done here (see parser.py): this node only prepares the visual layer so
the VLM can take over when the text layer is missing or fails validation. For PDF/DOCX it
also carries forward the text pypdfium produces as a byproduct of rendering pages, as a
last-resort fallback for the parser.
"""
import hashlib
import shutil
import subprocess
from pathlib import Path

from agent.logger import get_logger, log_node
from agent.state import HRState, RDEMError
from config import settings as S

_IMG = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}
_TXT = {".txt", ".md", ".json"}


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


def _office_to_pdf(path: Path, out_dir: Path) -> Path | None:
    """Word -> PDF with headless LibreOffice, so the VLM can SEE the layout when the text path fails.

    A private profile dir per conversion is required: LibreOffice locks its default profile, so two
    parallel conversions would otherwise fail or hang.
    """
    exe = shutil.which("soffice") or shutil.which("libreoffice")
    if not exe:
        get_logger().info("  [converter] LibreOffice not installed: Word file will use the text layer only")
        return None
    profile = out_dir / "lo_profile"
    try:
        subprocess.run(
            [exe, f"-env:UserInstallation=file://{profile.resolve()}", "--headless", "--convert-to", "pdf",
             "--outdir", str(out_dir), str(path)],
            check=True, capture_output=True, timeout=120)
    except Exception as e:
        get_logger().warning(f"  [converter] Word->PDF conversion failed: {type(e).__name__}: {str(e)[:200]}")
        return None
    pdf = out_dir / f"{path.stem}.pdf"
    return pdf if pdf.exists() else None


@log_node
def converter(state: HRState) -> dict:
    path = Path(state.cv_path)
    if not path.is_file():
        rdem = RDEMError(node="converter", error_type="file_not_found", message=f"{path} does not exist")
        return {"status": "failed", "global_error_log": [rdem], "_status": "error"}

    cid = hashlib.sha1(path.read_bytes()).hexdigest()[:10]
    out_dir = S.TMP_DIR / cid
    out_dir.mkdir(parents=True, exist_ok=True)
    ext = path.suffix.lower()
    pages: list[str] = []
    raw_text = ""

    try:
        if ext in _TXT:
            pass  # no page images needed; parser reads the file directly
        elif ext in _IMG:
            from PIL import Image

            p = out_dir / "page_1.png"
            _resize(Image.open(path).convert("RGB")).save(p)
            pages = [str(p)]
        elif ext == ".pdf":
            pages, raw_text = _render_pdf(path, out_dir)
        elif ext in {".docx", ".doc"}:
            pdf = _office_to_pdf(path, out_dir)
            if pdf:
                pages, raw_text = _render_pdf(pdf, out_dir)
        else:
            raise ValueError(f"unsupported file type '{ext}'")
    except Exception as e:
        rdem = RDEMError(node="converter", error_type="conversion_failed", message=f"{type(e).__name__}: {e}",
                         suggestion="Check the file is a valid, non-encrypted CV.")
        return {"status": "failed", "global_error_log": [rdem], "_status": "error"}

    get_logger().info(f"  [converter] id={cid} pages={len(pages)}")
    return {"candidate_id": cid, "page_paths": pages, "raw_text_layer": raw_text}
