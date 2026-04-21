from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from pathlib import Path

from api.admin import router as admin_router
from api.admin_eval import router as admin_eval_router
from api.routes import router as api_router

app = FastAPI(title="Extraction de Factures BTP")

BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

app.include_router(api_router)
app.include_router(admin_router)
app.include_router(admin_eval_router)


@app.get("/")
async def root():
    return RedirectResponse(url="/texte")


@app.get("/texte")
async def page_texte(request: Request):
    return templates.TemplateResponse(request=request, name="texte.html", context={"active": "texte"})


@app.get("/smart")
async def page_smart(request: Request):
    return templates.TemplateResponse(request=request, name="smart.html", context={"active": "smart"})


@app.get("/nouvelle")
async def page_nouvelle(request: Request):
    return templates.TemplateResponse(request=request, name="nouvelle.html", context={"active": "nouvelle"})


@app.get("/batch")
async def page_batch(request: Request):
    return templates.TemplateResponse(request=request, name="batch.html", context={"active": "batch"})


@app.get("/admin")
async def page_admin(request: Request):
    return templates.TemplateResponse(request=request, name="admin.html", context={"active": "admin"})


@app.get("/admin-lab")
async def page_admin_lab(request: Request):
    return templates.TemplateResponse(request=request, name="admin_lab.html", context={"active": "admin-lab"})


@app.get("/eval-lab")
async def page_eval_lab(request: Request):
    return templates.TemplateResponse(request=request, name="eval_lab.html", context={"active": "eval-lab"})
