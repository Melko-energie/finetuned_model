from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from pathlib import Path

from api.routes import router as api_router

app = FastAPI(title="Extraction de Factures BTP")

BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

app.include_router(api_router)


@app.get("/")
async def root():
    return RedirectResponse(url="/texte")


@app.get("/texte")
async def page_texte(request: Request):
    return templates.TemplateResponse("texte.html", {"request": request, "active": "texte"})


@app.get("/smart")
async def page_smart(request: Request):
    return templates.TemplateResponse("smart.html", {"request": request, "active": "smart"})


@app.get("/nouvelle")
async def page_nouvelle(request: Request):
    return templates.TemplateResponse("nouvelle.html", {"request": request, "active": "nouvelle"})


@app.get("/batch")
async def page_batch(request: Request):
    return templates.TemplateResponse("batch.html", {"request": request, "active": "batch"})
