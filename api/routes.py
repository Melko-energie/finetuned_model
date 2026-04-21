from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import io
import os

import json as json_module

from core.extraction import (
    extract_from_precomputed_ocr,
    extract_smart,
    process_file_live,
    get_fournisseurs_list,
)
from core.batch import iter_batch_zip, process_batch_zip
from core.excel import export_excel_batch, export_excel_multi_sheets

router = APIRouter(prefix="/api")


@router.get("/fournisseurs")
async def list_fournisseurs():
    return {"fournisseurs": get_fournisseurs_list()}


@router.post("/extract-texte")
async def api_extract_texte(file: UploadFile = File(...)):
    result = extract_from_precomputed_ocr(file.filename)
    return result


@router.post("/extract-smart")
async def api_extract_smart(
    file: UploadFile = File(...),
    fournisseur: str = Form("Auto-detect"),
):
    result = extract_smart(file.filename, fournisseur)
    return result


@router.post("/extract-ocr")
async def api_extract_ocr(
    file: UploadFile = File(...),
    fournisseur: str = Form("Auto-detect"),
):
    file_bytes = await file.read()
    suffix = os.path.splitext(file.filename)[1].lower()
    result = process_file_live(file_bytes, suffix, fournisseur)
    return result


@router.post("/batch")
async def api_batch(file: UploadFile = File(...)):
    zip_bytes = await file.read()

    def event_stream():
        results = []
        for idx, total, result in iter_batch_zip(zip_bytes):
            results.append(result)
            event = {
                "type": "progress",
                "index": idx + 1,
                "total": total,
                "result": result,
            }
            yield f"data: {json_module.dumps(event, ensure_ascii=False)}\n\n"
        # Final event with all results
        yield f"data: {json_module.dumps({'type': 'done', 'results': results, 'total': len(results)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


class ExportRequest(BaseModel):
    results: list[dict]


@router.post("/export-excel")
async def api_export_excel(data: ExportRequest):
    xlsx_bytes = export_excel_batch(data.results)
    return StreamingResponse(
        io.BytesIO(xlsx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=extraction.xlsx"},
    )


@router.post("/export-excel-multi")
async def api_export_excel_multi(data: ExportRequest):
    xlsx_bytes = export_excel_multi_sheets(data.results)
    return StreamingResponse(
        io.BytesIO(xlsx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=extraction_multi.xlsx"},
    )


