#!/usr/bin/env python3
"""
Router CLI — Pipeline LayoutLMv3 BTP Invoice NER
Usage:
    python run.py --all              # Lance tout le pipeline (01 → 05)
    python run.py --from 3           # Lance à partir de l'étape 3
    python run.py --step 5           # Lance uniquement l'étape 5
    python run.py --list             # Affiche toutes les étapes
"""

import subprocess
import sys
import argparse
import time
import os
from pathlib import Path

# ── Couleurs terminal ──────────────────────────────────────────────
class C:
    RESET  = "\033[0m"
    BOLD   = "\033[1m"
    GREEN  = "\033[92m"
    YELLOW = "\033[93m"
    RED    = "\033[91m"
    CYAN   = "\033[96m"
    GREY   = "\033[90m"
    WHITE  = "\033[97m"

# ── Définition des étapes ──────────────────────────────────────────
STEPS = [
    {
        "id": 0,
        "name": "PDF → Images PNG",
        "script": "scripts/00_pdf_to_images.py",
        "desc": "Convertit les PDFs en images pour LabelStudio",
        "optional": True,
    },
    {
        "id": 1,
        "name": "OCR Extraction",
        "script": "scripts/01_ocr_extraction.py",
        "desc": "Extrait tokens + bounding boxes via DocTR",
        "optional": False,
    },
    {
        "id": 2,
        "name": "Auto-Labeling",
        "script": "scripts/02_auto_labeling.py",
        "desc": "Génère les annotations automatiques par regex",
        "optional": False,
    },
    {
        "id": 3,
        "name": "Nettoyage",
        "script": "scripts/03_label_cleaner.py",
        "desc": "Supprime invalides et doublons",
        "optional": False,
    },
    {
        "id": 4,
        "name": "Dataset Builder",
        "script": "scripts/04_dataset_builder.py",
        "desc": "Construit le dataset HuggingFace",
        "optional": False,
    },
    {
        "id": 5,
        "name": "Training",
        "script": "scripts/05_train_model.py",
        "desc": "Fine-tune LayoutLMv3 avec LoRA",
        "optional": False,
    },
    {
        "id": 6,
        "name": "Inférence",
        "script": "scripts/06_inference.py",
        "desc": "Prédit les entités sur nouvelles factures",
        "optional": True,
    },
]

# ── Helpers ────────────────────────────────────────────────────────
ROOT = Path(__file__).parent

def print_header():
    print(f"\n{C.CYAN}{C.BOLD}{'═' * 58}")
    print(f"  LayoutLMv3 BTP Invoice NER — Pipeline Router")
    print(f"{'═' * 58}{C.RESET}\n")

def print_step_list():
    print(f"{C.BOLD}  Étapes disponibles :{C.RESET}\n")
    for step in STEPS:
        optional = f"{C.GREY}[optionnel]{C.RESET}" if step["optional"] else ""
        print(f"  {C.CYAN}{step['id']:>2}{C.RESET}  {C.WHITE}{step['name']:<22}{C.RESET}  {C.GREY}{step['desc']}{C.RESET} {optional}")
    print()

def print_step_start(step):
    print(f"\n{C.CYAN}{'─' * 58}{C.RESET}")
    print(f"{C.BOLD}  [{step['id']}] {step['name']}{C.RESET}")
    print(f"  {C.GREY}{step['desc']}{C.RESET}")
    print(f"  {C.GREY}Script : {step['script']}{C.RESET}")
    print(f"{C.CYAN}{'─' * 58}{C.RESET}\n")

def print_step_result(step, success, duration):
    status = f"{C.GREEN}✓ SUCCÈS{C.RESET}" if success else f"{C.RED}✗ ÉCHEC{C.RESET}"
    print(f"\n  {status}  {C.GREY}({duration:.1f}s){C.RESET}  {C.WHITE}{step['name']}{C.RESET}")

def print_summary(results):
    print(f"\n{C.CYAN}{C.BOLD}{'═' * 58}")
    print(f"  Résumé pipeline")
    print(f"{'═' * 58}{C.RESET}\n")
    
    total   = len(results)
    success = sum(1 for r in results if r["success"])
    failed  = total - success

    for r in results:
        icon = f"{C.GREEN}✓{C.RESET}" if r["success"] else f"{C.RED}✗{C.RESET}"
        print(f"  {icon}  {r['name']:<22}  {C.GREY}{r['duration']:.1f}s{C.RESET}")

    print(f"\n  {C.BOLD}Total : {success}/{total} étapes réussies{C.RESET}")
    
    if failed > 0:
        print(f"  {C.RED}{failed} étape(s) en échec{C.RESET}")
    else:
        print(f"  {C.GREEN}Pipeline complet ✓{C.RESET}")
    print()

def run_step(step) -> tuple[bool, float]:
    script_path = ROOT / step["script"]

    if not script_path.exists():
        print(f"  {C.RED}✗ Script introuvable : {script_path}{C.RESET}")
        return False, 0.0

    start = time.time()
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(ROOT / "scripts"),
            check=False
        )
        duration = time.time() - start
        success = result.returncode == 0

        if not success:
            print(f"\n  {C.RED}✗ Le script a retourné le code {result.returncode}{C.RESET}")

        return success, duration

    except KeyboardInterrupt:
        duration = time.time() - start
        print(f"\n  {C.YELLOW}⚠ Interrompu par l'utilisateur{C.RESET}")
        return False, duration

    except Exception as e:
        duration = time.time() - start
        print(f"\n  {C.RED}✗ Erreur inattendue : {e}{C.RESET}")
        return False, duration

def run_steps(steps_to_run: list[dict], stop_on_error: bool = True):
    results = []

    for step in steps_to_run:
        print_step_start(step)
        success, duration = run_step(step)
        print_step_result(step, success, duration)

        results.append({
            "name": step["name"],
            "success": success,
            "duration": duration
        })

        if not success and stop_on_error:
            print(f"\n  {C.RED}Pipeline arrêté à l'étape {step['id']} — {step['name']}{C.RESET}")
            print(f"  {C.GREY}Relance depuis cette étape : python run.py --from {step['id']}{C.RESET}\n")
            break

    print_summary(results)

# ── Main ───────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Router CLI — Pipeline LayoutLMv3 BTP",
        formatter_class=argparse.RawTextHelpFormatter
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--all",
        action="store_true",
        help="Lance tout le pipeline (étapes 1 → 5)"
    )
    group.add_argument(
        "--from",
        dest="from_step",
        type=int,
        metavar="N",
        help="Lance à partir de l'étape N jusqu'à la fin"
    )
    group.add_argument(
        "--step",
        type=int,
        metavar="N",
        help="Lance uniquement l'étape N"
    )
    group.add_argument(
        "--list",
        action="store_true",
        help="Affiche toutes les étapes disponibles"
    )
    parser.add_argument(
        "--no-stop",
        action="store_true",
        help="Continue même en cas d'erreur"
    )

    args = parser.parse_args()

    print_header()

    # Étapes principales (sans les optionnelles par défaut)
    main_steps = [s for s in STEPS if not s["optional"]]
    all_steps  = STEPS

    if args.list:
        print_step_list()
        return

    if args.all:
        print(f"  {C.BOLD}Mode : Pipeline complet (étapes 1 → 5){C.RESET}\n")
        run_steps(main_steps, stop_on_error=not args.no_stop)

    elif args.from_step is not None:
        ids = [s["id"] for s in all_steps]
        if args.from_step not in ids:
            print(f"  {C.RED}✗ Étape {args.from_step} introuvable.{C.RESET}")
            print_step_list()
            sys.exit(1)
        steps = [s for s in all_steps if s["id"] >= args.from_step and not s["optional"]]
        print(f"  {C.BOLD}Mode : À partir de l'étape {args.from_step}{C.RESET}\n")
        run_steps(steps, stop_on_error=not args.no_stop)

    elif args.step is not None:
        ids = [s["id"] for s in all_steps]
        if args.step not in ids:
            print(f"  {C.RED}✗ Étape {args.step} introuvable.{C.RESET}")
            print_step_list()
            sys.exit(1)
        step = next(s for s in all_steps if s["id"] == args.step)
        print(f"  {C.BOLD}Mode : Étape unique — {step['name']}{C.RESET}\n")
        run_steps([step], stop_on_error=not args.no_stop)


if __name__ == "__main__":
    main()