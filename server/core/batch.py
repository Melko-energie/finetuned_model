"""ZIP batch processing: iterate invoices, fall back to live OCR when no
pre-computed JSON exists."""

import io
import os
import zipfile

from core.config import ALL_FIELD_KEYS
from core.detection import detect_installateur, detect_avoir
from core.ocr import get_ocr_text
from core.postprocess import inverser_montants_avoir
from core.extraction import extraire_champs, process_file_live


def iter_batch_zip(zip_bytes: bytes):
    """Yield (index, total, result_dict) for each invoice in the ZIP.

    Tries pre-computed OCR first; falls back to live DocTR. Errors are
    swallowed and surfaced as `installateur="ERREUR"` rows so the SSE stream
    keeps progressing.
    """
    zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
    valid_ext = {".pdf", ".png", ".jpg", ".jpeg"}
    file_names = sorted(
        n for n in zf.namelist()
        if not n.startswith("__") and not n.endswith("/")
        and os.path.splitext(n)[1].lower() in valid_ext
    )
    total = len(file_names)

    for idx, fname in enumerate(file_names):
        short_name = os.path.basename(fname)

        texte = get_ocr_text(short_name)
        if texte:
            installateur = detect_installateur(texte)
            is_avoir = detect_avoir(texte)
            fields = extraire_champs(texte, installateur)
            if is_avoir and fields:
                fields = inverser_montants_avoir(fields)
            if fields:
                yield idx, total, {
                    "filename": short_name,
                    "fields": fields,
                    "installateur": installateur or "DEFAULT",
                    "is_avoir": is_avoir,
                    "source": "OCR pre-calcule",
                }
                continue

        try:
            file_bytes = zf.read(fname)
            suffix = os.path.splitext(fname)[1].lower()
            res = process_file_live(file_bytes, suffix, "Auto-detect")
            if res["fields"] and not res["error"]:
                yield idx, total, {
                    "filename": short_name,
                    "fields": res["fields"],
                    "installateur": res["installateur"] or "DEFAULT",
                    "is_avoir": res["is_avoir"],
                    "source": "DocTR live",
                }
            else:
                yield idx, total, {
                    "filename": short_name,
                    "fields": {k: None for k in ALL_FIELD_KEYS},
                    "installateur": "ERREUR",
                    "is_avoir": False,
                    "source": res["error"] or "Echec extraction",
                }
        except Exception as e:
            yield idx, total, {
                "filename": short_name,
                "fields": {k: None for k in ALL_FIELD_KEYS},
                "installateur": "ERREUR",
                "is_avoir": False,
                "source": str(e),
            }


def process_batch_zip(zip_bytes: bytes) -> list[dict]:
    """Drain `iter_batch_zip` into a list. Useful for non-streaming callers."""
    return [result for _, _, result in iter_batch_zip(zip_bytes)]
