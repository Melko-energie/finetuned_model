# syntax=docker/dockerfile:1.7
# Image de l'app Extraction Factures BTP.
# Conçue pour être lancée via docker-compose, qui :
#   - publie le port 8001 vers l'hôte
#   - monte server/data/ et server/config/prompts/ pour persistance + édition à chaud
#   - injecte OLLAMA_HOST pour pointer sur l'Ollama du host

FROM python:3.11-slim AS base

# Dépendances système pour OpenCV (libgl + glib) et fontconfig pour DocTR
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
        libfontconfig1 \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Installer les deps Python d'abord — couche cachée tant que requirements.txt
# ne change pas, ce qui rend les rebuilds rapides après modif du code.
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Code applicatif. Note : .dockerignore exclut venv/, server/data/, docs/,
# .git/, etc. — l'image ne contient que ce qui est strictement nécessaire.
COPY server/ ./server/
COPY ui/ ./ui/

# Le container expose 8001 vers le réseau interne docker.
EXPOSE 8001

# Healthcheck : ping de la page racine. Si elle ne répond pas → container unhealthy.
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8001/texte', timeout=3)" || exit 1

# Lancement direct (pas via start.py — le setup est déjà fait au build).
# --host 0.0.0.0 pour que le container accepte les connexions venant de l'hôte.
CMD ["uvicorn", "main:app", "--app-dir", "server", "--host", "0.0.0.0", "--port", "8001"]
