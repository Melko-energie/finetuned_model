.PHONY: help install run ocr cli clean

# Detect venv python: Windows uses venv/Scripts/, Unix uses venv/bin/
PYTHON := $(shell test -x venv/Scripts/python.exe && echo venv/Scripts/python.exe || echo venv/bin/python)
UVICORN := $(shell test -x venv/Scripts/uvicorn.exe && echo venv/Scripts/uvicorn.exe || echo venv/bin/uvicorn)
PORT ?= 8001

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-12s %s\n", $$1, $$2}'

install: ## Create venv and install Python dependencies
	@test -d venv || python -m venv venv
	@$(PYTHON) -m pip install --upgrade pip
	@$(PYTHON) -m pip install -r requirements.txt
	@echo ""
	@echo "Done. Don't forget: ollama pull gemma2:9b"

run: ## Launch the FastAPI app (PORT=8001 by default)
	@$(UVICORN) main:app --reload --port $(PORT)

ocr: ## Run OCR pipeline: PDF -> PNG -> JSON
	@$(PYTHON) scripts/pdf_to_images.py
	@$(PYTHON) scripts/run_ocr.py

cli: ## Smoke test: extract 3 reference invoices
	@$(PYTHON) scripts/extract_cli.py

clean: ## Remove __pycache__ directories
	@find . -path ./venv -prune -o -type d -name '__pycache__' -print -exec rm -rf {} + 2>/dev/null || true
