"""Admin endpoints for the evaluation pipeline (chantier 2.6).

Separate from api/admin.py (prompts CRUD) to keep each file focused.
Shares the _require_localhost dependency.
"""

import io
import json
import tempfile
import zipfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse

from api.admin import _require_localhost
from core.eval.diff import diff_results
from core.eval.excel_report import dump_excel
from core.eval.history import RUNS_DIR, list_runs, load_run, save_run
from core.eval.runner import iter_run_eval, run_eval

router = APIRouter(prefix="/api/admin/eval", dependencies=[Depends(_require_localhost)])


@router.post("")
async def run_evaluation(
    pdfs_zip: UploadFile = File(...),
    truth_xlsx: UploadFile = File(...),
):
    """Execute a full evaluation run from an uploaded ZIP + XLSX.

    Saves the result under data/eval_runs/<timestamp>/ and returns the
    full result plus a download URL for the generated XLSX report.
    """
    if not pdfs_zip.filename or not pdfs_zip.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="pdfs_zip must be a .zip file")
    if not truth_xlsx.filename or not truth_xlsx.filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="truth_xlsx must be a .xlsx file")

    zip_bytes = await pdfs_zip.read()
    truth_bytes = await truth_xlsx.read()

    with tempfile.TemporaryDirectory() as tmp_str:
        tmp = Path(tmp_str)
        pdfs_dir = tmp / "pdfs"
        pdfs_dir.mkdir()

        try:
            with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
                zf.extractall(pdfs_dir)
        except zipfile.BadZipFile:
            raise HTTPException(status_code=400, detail="pdfs_zip is not a valid ZIP archive")

        truth_path = tmp / "truth.xlsx"
        truth_path.write_bytes(truth_bytes)

        try:
            result = run_eval(pdfs_dir, truth_path)
        except (FileNotFoundError, ValueError) as e:
            raise HTTPException(status_code=400, detail=str(e))

    if result["meta"]["matched"] == 0:
        raise HTTPException(
            status_code=400,
            detail="No PDFs matched the ground truth — check filenames.",
        )

    run_dir = save_run(result)
    dump_excel(result, run_dir / "report.xlsx")

    return {
        "run_id": run_dir.name,
        "result": result,
        "download_url": f"/api/admin/eval/runs/{run_dir.name}/download",
    }


@router.post("/stream")
async def run_evaluation_stream(
    pdfs_zip: UploadFile = File(...),
    truth_xlsx: UploadFile = File(...),
):
    """SSE variant of POST /api/admin/eval (chantier 5.4).

    Emits init / progress / done events as the pipeline advances. Fail-fast
    validation (bad ZIP, wrong extension) returns a synchronous 400 before
    any event is sent; errors raised mid-pipeline surface as a single
    {type: error} event.
    """
    if not pdfs_zip.filename or not pdfs_zip.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="pdfs_zip must be a .zip file")
    if not truth_xlsx.filename or not truth_xlsx.filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="truth_xlsx must be a .xlsx file")

    zip_bytes = await pdfs_zip.read()
    truth_bytes = await truth_xlsx.read()

    def event_stream():
        with tempfile.TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            pdfs_dir = tmp / "pdfs"
            pdfs_dir.mkdir()
            try:
                with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
                    zf.extractall(pdfs_dir)
            except zipfile.BadZipFile:
                yield f"data: {json.dumps({'type': 'error', 'error': 'pdfs_zip is not a valid ZIP archive'}, ensure_ascii=False)}\n\n"
                return

            truth_path = tmp / "truth.xlsx"
            truth_path.write_bytes(truth_bytes)

            try:
                for event in iter_run_eval(pdfs_dir, truth_path):
                    if event["type"] == "done":
                        result = event["result"]
                        if result["meta"]["matched"] > 0:
                            run_dir = save_run(result)
                            try:
                                dump_excel(result, run_dir / "report.xlsx")
                            except Exception:
                                pass  # XLSX is a bonus, don't fail the run
                            event["run_id"] = run_dir.name
                            event["download_url"] = f"/api/admin/eval/runs/{run_dir.name}/download"
                    yield f"data: {json.dumps(event, default=str, ensure_ascii=False)}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'error': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/runs")
async def list_eval_runs():
    runs = list_runs()
    # Path objects aren't JSON-serializable; strip them
    return {"runs": [{k: v for k, v in r.items() if k != "path"} for r in runs]}


@router.get("/runs/{run_id}")
async def get_eval_run(run_id: str):
    try:
        return load_run(run_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/runs/{run_id}/download")
async def download_eval_xlsx(run_id: str):
    xlsx_path = RUNS_DIR / run_id / "report.xlsx"
    if not xlsx_path.is_file():
        raise HTTPException(
            status_code=404,
            detail=f"No XLSX report for run '{run_id}'.",
        )
    return FileResponse(
        xlsx_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=f"{run_id}.xlsx",
    )


@router.get("/runs/{run_a}/diff/{run_b}")
async def diff_eval_runs(run_a: str, run_b: str):
    try:
        a = load_run(run_a)
        b = load_run(run_b)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return diff_results(a, b)
