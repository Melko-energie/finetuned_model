#!/usr/bin/env python
"""start.py — Lanceur cross-platform du projet Extraction Factures BTP.

Remplace le Makefile pour ne pas dépendre de l'outil `make` (souvent absent
sur Windows). Tourne sur n'importe quelle machine où Python est installé.

Usage :
    python start.py                  # = 'go' : tout-en-un (recommandé)
    python start.py go               # idem, explicite
    python start.py install          # juste venv + deps Python
    python start.py check            # diagnostique Ollama + modèle
    python start.py run              # juste lance uvicorn
    python start.py ocr              # pipeline PDFs -> PNG -> JSON
    python start.py cli              # smoke test sur 3 factures
    python start.py eval --pdfs DIR --truth FILE.xlsx
    python start.py clean            # supprime les __pycache__

Variables :
    --port 8002                       change le port (défaut 8001)
    --model gemma3:latest             change le modèle Ollama
"""

import argparse
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV = ROOT / "venv"
IS_WINDOWS = platform.system() == "Windows"

# Bin paths inside venv — computed lazily because venv may not exist yet
def _venv_bin(name: str) -> Path:
    sub = "Scripts" if IS_WINDOWS else "bin"
    suffix = ".exe" if IS_WINDOWS else ""
    return VENV / sub / f"{name}{suffix}"

DEFAULT_PORT = 8001
DEFAULT_MODEL = "gemma2:9b"


# ─── UI helpers ────────────────────────────────────────────────────────

def _force_utf8():
    """Make Unicode output (✅, →, etc.) work on Windows cp1252 terminals."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def banner(text: str) -> None:
    print()
    print("=" * 64)
    print(f"  {text}")
    print("=" * 64)
    print()


def step(n: int, total: int, text: str) -> None:
    print(f"[{n}/{total}] {text}")


# ─── Sub-commands ──────────────────────────────────────────────────────

def cmd_install(verbose: bool = False) -> None:
    """Crée le venv (si absent) et installe / met à jour les dépendances."""
    if not VENV.is_dir():
        print(f"  → venv absent, création dans {VENV.relative_to(ROOT)}...")
        subprocess.run([sys.executable, "-m", "venv", str(VENV)], check=True, cwd=ROOT)
    else:
        print(f"  → venv OK ({VENV.relative_to(ROOT)})")

    python = _venv_bin("python")
    pip_install = [str(python), "-m", "pip", "install"]
    if not verbose:
        pip_install.append("--quiet")

    subprocess.run([str(python), "-m", "pip", "install", "--quiet", "--upgrade", "pip"],
                   check=True, cwd=ROOT)
    subprocess.run(pip_install + ["-r", str(ROOT / "requirements.txt")],
                   check=True, cwd=ROOT)
    print("  → dépendances Python installées")


def cmd_check(model: str = DEFAULT_MODEL) -> None:
    """Vérifie qu'Ollama tourne et que le modèle est dispo. Pull si manquant."""
    if not shutil.which("ollama"):
        print("❌ Ollama n'est pas installé sur ce système.")
        print("   → Télécharge-le sur https://ollama.com")
        sys.exit(1)

    try:
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=5)
    except (subprocess.TimeoutExpired, OSError):
        print("❌ Ollama ne répond pas (timeout).")
        print("   → Lance Ollama Desktop ou 'ollama serve' puis réessaie.")
        sys.exit(1)

    if result.returncode != 0:
        print("❌ Ollama ne répond pas.")
        print("   → Lance Ollama Desktop ou 'ollama serve' puis réessaie.")
        sys.exit(1)

    # Tolère les variantes de tag : "gemma2:9b" matche aussi "gemma2:latest"
    base = model.split(":")[0]
    found = False
    for line in result.stdout.splitlines():
        if not line.strip() or line.startswith("NAME"):
            continue
        first = line.split()[0]  # ex: "gemma2:latest"
        if first.split(":")[0] == base:
            found = True
            break

    if not found:
        print(f"  📥 Modèle {model} absent, téléchargement (~5.4 GB)...")
        subprocess.run(["ollama", "pull", model], check=True)
    else:
        print(f"  → Ollama OK + modèle {base} présent")


def cmd_run(port: int = DEFAULT_PORT) -> None:
    """Lance uvicorn sur le port donné. Suppose tout déjà installé."""
    uvicorn = _venv_bin("uvicorn")
    if not uvicorn.is_file():
        print(f"❌ uvicorn introuvable dans {VENV.relative_to(ROOT)}.")
        print("   → Lance d'abord 'python start.py install'.")
        sys.exit(1)

    print(f"  → http://127.0.0.1:{port}")
    print(f"  → Ctrl+C pour arrêter")
    print()
    subprocess.run([str(uvicorn), "main:app", "--reload",
                    "--port", str(port), "--app-dir", "server"], cwd=ROOT)


def cmd_go(port: int = DEFAULT_PORT, model: str = DEFAULT_MODEL) -> None:
    """⭐ Tout-en-un : setup + check Ollama + lance le serveur."""
    banner("Démarrage de l'app Extraction Factures BTP")

    step(1, 4, "Vérification du venv et des dépendances Python...")
    cmd_install()
    print()

    step(2, 4, "Vérification d'Ollama...")
    cmd_check(model)
    print()

    step(3, 4, "Tout est prêt.")
    print()

    step(4, 4, f"Démarrage du serveur FastAPI sur le port {port}...")
    cmd_run(port)


def cmd_ocr() -> None:
    """Pipeline OCR : PDFs sous server/data/raw_pdfs/ → PNG → JSON DocTR."""
    python = _venv_bin("python")
    subprocess.run([str(python), str(ROOT / "server" / "scripts" / "pdf_to_images.py")],
                   check=True, cwd=ROOT)
    subprocess.run([str(python), str(ROOT / "server" / "scripts" / "run_ocr.py")],
                   check=True, cwd=ROOT)


def cmd_cli() -> None:
    """Smoke test : extraction sur 3 factures de référence (A2M, ESTEVE, TERNEL)."""
    python = _venv_bin("python")
    subprocess.run([str(python), str(ROOT / "server" / "scripts" / "extract_cli.py")],
                   check=True, cwd=ROOT)


def cmd_eval(pdfs: str, truth: str) -> None:
    """Banc d'évaluation CLI."""
    python = _venv_bin("python")
    subprocess.run([str(python), str(ROOT / "server" / "scripts" / "run_eval.py"),
                    "run", "--pdfs", pdfs, "--truth", truth],
                   check=True, cwd=ROOT)


def cmd_clean() -> None:
    """Supprime les __pycache__ (sauf dans venv/)."""
    count = 0
    for p in ROOT.rglob("__pycache__"):
        if "venv" in p.parts or "node_modules" in p.parts:
            continue
        shutil.rmtree(p, ignore_errors=True)
        count += 1
    print(f"  → {count} dossiers __pycache__ supprimés")


# ─── CLI parser ────────────────────────────────────────────────────────

def main() -> None:
    _force_utf8()

    parser = argparse.ArgumentParser(
        description="Lanceur du projet Extraction Factures BTP — alternative au Makefile.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Sans argument, équivaut à 'python start.py go' (tout-en-un).

Exemples :
  python start.py                              démarre tout
  python start.py go --port 8002               idem, port 8002
  python start.py install                      juste setup
  python start.py eval --pdfs data/lot --truth gt.xlsx
""",
    )
    parser.add_argument("--port", type=int, default=DEFAULT_PORT,
                        help=f"port d'écoute uvicorn (défaut {DEFAULT_PORT})")
    parser.add_argument("--model", default=DEFAULT_MODEL,
                        help=f"modèle Ollama (défaut {DEFAULT_MODEL})")

    sub = parser.add_subparsers(dest="cmd", metavar="<command>")
    sub.add_parser("go", help="⭐ Tout-en-un : setup + check Ollama + serveur")
    sub.add_parser("install", help="Crée le venv et installe les deps Python")
    sub.add_parser("check", help="Vérifie qu'Ollama tourne et que le modèle est dispo")
    sub.add_parser("run", help="Lance uvicorn (suppose tout installé)")
    sub.add_parser("ocr", help="Pipeline OCR : PDFs -> PNG -> JSON")
    sub.add_parser("cli", help="Smoke test sur 3 factures de référence")
    p_eval = sub.add_parser("eval", help="Lance le banc d'évaluation CLI")
    p_eval.add_argument("--pdfs", required=True, help="Dossier contenant les PDFs")
    p_eval.add_argument("--truth", required=True, help="Chemin vers le fichier ground truth Excel")
    sub.add_parser("clean", help="Supprime les caches __pycache__")

    args = parser.parse_args()
    cmd = args.cmd or "go"

    try:
        if cmd == "go":
            cmd_go(args.port, args.model)
        elif cmd == "install":
            cmd_install()
        elif cmd == "check":
            cmd_check(args.model)
        elif cmd == "run":
            cmd_run(args.port)
        elif cmd == "ocr":
            cmd_ocr()
        elif cmd == "cli":
            cmd_cli()
        elif cmd == "eval":
            cmd_eval(args.pdfs, args.truth)
        elif cmd == "clean":
            cmd_clean()
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Commande échouée (exit code {e.returncode})", file=sys.stderr)
        sys.exit(e.returncode)
    except KeyboardInterrupt:
        print("\n⏹  Interrompu par l'utilisateur.")
        sys.exit(130)


if __name__ == "__main__":
    main()
