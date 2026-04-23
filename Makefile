.PHONY: help go install ollama-check run ocr cli eval clean

# Detect venv python: Windows uses venv/Scripts/, Unix uses venv/bin/
PYTHON := $(shell test -x venv/Scripts/python.exe && echo venv/Scripts/python.exe || echo venv/bin/python)
UVICORN := $(shell test -x venv/Scripts/uvicorn.exe && echo venv/Scripts/uvicorn.exe || echo venv/bin/uvicorn)
PORT ?= 8001
MODEL ?= gemma2:9b

help: ## Show this help
	@echo "Usage : make <target>"
	@echo ""
	@echo "Cibles disponibles :"
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-14s %s\n", $$1, $$2}'
	@echo ""
	@echo "Variables : PORT=$(PORT)  MODEL=$(MODEL)"

go: ## ⭐ Tout-en-un : venv + deps + check Ollama + lance le serveur
	@echo ""
	@echo "════════════════════════════════════════════════════════════════"
	@echo "  Démarrage de l'app Extraction Factures BTP"
	@echo "════════════════════════════════════════════════════════════════"
	@echo ""
	@echo "[1/4] Vérification du venv..."
	@if [ ! -d venv ]; then \
		echo "  → venv absent, création en cours..."; \
		python -m venv venv; \
	else \
		echo "  → venv OK"; \
	fi
	@echo ""
	@echo "[2/4] Installation / mise à jour des dépendances Python..."
	@$(PYTHON) -m pip install --quiet --upgrade pip
	@$(PYTHON) -m pip install --quiet -r requirements.txt
	@echo "  → 15 dépendances OK"
	@echo ""
	@echo "[3/4] Vérification d'Ollama..."
	@if ! ollama list >/dev/null 2>&1; then \
		echo "  ❌ Ollama ne répond pas."; \
		echo "     Lance Ollama Desktop (ou 'ollama serve') puis réessaie."; \
		exit 1; \
	fi
	@MODEL_BASE=$$(echo $(MODEL) | cut -d: -f1); \
	if ! ollama list 2>/dev/null | grep -qE "^$$MODEL_BASE(:|\\s)"; then \
		echo "  📥 Modèle $(MODEL) absent, téléchargement (~5.4 GB)..."; \
		ollama pull $(MODEL); \
	else \
		echo "  → Ollama OK + modèle $$MODEL_BASE présent"; \
	fi
	@echo ""
	@echo "[4/4] Démarrage du serveur FastAPI sur le port $(PORT)..."
	@echo "      → http://127.0.0.1:$(PORT)"
	@echo "      → Ctrl+C pour arrêter"
	@echo ""
	@$(UVICORN) main:app --reload --port $(PORT) --app-dir server

install: ## Crée le venv et installe les dépendances Python (sans lancer)
	@test -d venv || python -m venv venv
	@$(PYTHON) -m pip install --upgrade pip
	@$(PYTHON) -m pip install -r requirements.txt
	@echo ""
	@echo "Done. N'oublie pas : ollama pull $(MODEL)"

ollama-check: ## Vérifie qu'Ollama tourne et que le modèle est dispo
	@ollama list >/dev/null 2>&1 || (echo "❌ Ollama ne répond pas" && exit 1)
	@MODEL_BASE=$$(echo $(MODEL) | cut -d: -f1); \
	ollama list 2>/dev/null | grep -qE "^$$MODEL_BASE(:|\\s)" || (echo "❌ Modèle $$MODEL_BASE absent — lance 'ollama pull $(MODEL)'" && exit 1); \
	echo "✅ Ollama OK + modèle $$MODEL_BASE présent"

run: ## Lance le serveur FastAPI (suppose tout déjà installé)
	@$(UVICORN) main:app --reload --port $(PORT) --app-dir server

ocr: ## Pipeline OCR : PDFs → PNG → JSON DocTR
	@$(PYTHON) server/scripts/pdf_to_images.py
	@$(PYTHON) server/scripts/run_ocr.py

cli: ## Smoke test : extraction sur 3 factures de référence
	@$(PYTHON) server/scripts/extract_cli.py

eval: ## Lance le banc d'évaluation en CLI (PDFS=... TRUTH=...)
	@if [ -z "$(PDFS)" ] || [ -z "$(TRUTH)" ]; then \
		echo "Usage : make eval PDFS=<dossier> TRUTH=<truth.xlsx>"; \
		exit 1; \
	fi
	@$(PYTHON) server/scripts/run_eval.py run --pdfs $(PDFS) --truth $(TRUTH)

clean: ## Supprime les caches __pycache__
	@find . -path ./venv -prune -o -type d -name '__pycache__' -print -exec rm -rf {} + 2>/dev/null || true
