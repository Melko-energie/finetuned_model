# UI de génération — Design (chantier 4.3)

**Date** : 2026-04-21
**Chantier** : 4.3 (UI dans `/admin-lab`, branche l'endpoint 4.2)
**Prérequis** : 4.1 + 4.2
**Statut** : validé, implémentation en cours

---

## Objectif

Permettre au métier, depuis `/admin-lab`, de fournir 2-5 factures PDF + un Excel ground truth → l'application génère un brouillon de prompt → le métier relit, corrige et valide via l'éditeur existant.

**Boucle livrée** : upload → OCR + génération LLM (~30-60 s) → draft pré-rempli dans l'éditeur → review → save (via l'endpoint CRUD existant).

## Décisions clés

| Décision | Choix | Justification |
|---|---|---|
| Fichiers modifiés | Seulement `templates/admin_lab.html` + `static/js/admin_lab.js` | `/admin` stable reste intact. |
| Déclencheur | Bouton "Générer depuis des factures" à côté de "+ Nouveau" | Discoverable, cohérent avec la position des actions globales. |
| Saisie | Modale par-dessus la page | Contexte concentré, pas de navigation, facile à annuler. |
| Draft result | Pré-remplit l'éditeur existant, passe en mode "nouveau prompt" | Zéro nouveau flow à apprendre, la Save button est déjà connue. |
| Inputs fichiers | `<input type="file" multiple accept=".pdf">` + un input séparé pour XLSX | Suffisant au premier jet. Drag-drop peut s'ajouter plus tard. |
| Validation client | Regex clé, 2-5 PDFs | Défense en profondeur — le serveur valide aussi. |
| État "loading" | Bouton désactivé + spinner + texte explicite ("~30s") | Le process est long, l'utilisateur doit comprendre qu'il attend. |
| Gestion erreur | Toast rouge + modale reste ouverte + form intact | Permet de corriger sans tout retaper. |

## Contrat UI

### Bouton "Générer depuis des factures"

Placé dans le header, à gauche de "+ Nouveau" :

```
[Générer depuis des factures]   [+ Nouveau prompt]
      icône: science             icône: add
```

### Modale

- Titre : "Générer un prompt depuis des factures"
- Champs :
  - **Clé du nouveau fournisseur** (input text, regex validé côté JS)
  - **Factures échantillons (2 à 5 PDFs)** — input file multiple + liste des fichiers choisis en dessous
  - **Excel ground truth** — input file simple, accept `.xlsx`
  - Paragraphe d'aide : "L'Excel doit contenir une ligne par PDF avec les valeurs attendues. Format = sortie Excel de la page Traitement par lot."
- Actions :
  - **Annuler** (gris)
  - **Générer** (primary) — devient "Génération en cours (~30s)…" + disabled pendant le fetch
- Bande de loading pendant l'appel : barre/spinner + texte

### Flow après succès

1. Modale se ferme automatiquement.
2. L'éditeur existant affiche le draft : `key`, `detecter`, `prompt`.
3. Badge "brouillon" (couleur tertiaire) au lieu de `supplier`.
4. Mode `isNew=true`, `isDirty=true` → le bouton Save est actif, le dot orange visible.
5. Toast vert : "Brouillon généré — relis et sauvegarde".
6. L'utilisateur relit/corrige, clique **Sauvegarder** (flow existant) → `POST /api/admin/prompts` → persiste + reload automatique.

### Flow après erreur

- Modale reste ouverte, form intact.
- Toast rouge avec le message du serveur (`detail`).
- Loading state effacé.

## Structure JS

Ajouter dans l'IIFE de `admin_lab.js` :

```js
const state = { ..., isGenerating: false };

// DOM refs for the new elements
const btnGenerate = $("btn-generate");
const modalGenerate = $("modal-generate");
const genForm = $("gen-form");
const genKey = $("gen-key");
const genPdfs = $("gen-pdfs");
const genPdfsList = $("gen-pdfs-list");
const genTruth = $("gen-truth");
const btnGenSubmit = $("btn-gen-submit");
const btnGenCancel = $("btn-gen-cancel");
const genLoading = $("gen-loading");

function openGenerateModal() { ... }
function closeGenerateModal() { ... }
async function submitGenerate(event) { ... }
function loadDraft(draft) { ... }

// Event wiring
btnGenerate.addEventListener("click", openGenerateModal);
btnGenCancel.addEventListener("click", closeGenerateModal);
genForm.addEventListener("submit", submitGenerate);
genPdfs.addEventListener("change", updatePdfsList);
```

### Distinction onTextareaChange en mode isNew

Actuellement, quand `isNew` est vrai mais que l'utilisateur n'a pas modifié les textareas, `onTextareaChange` peut les considérer "clean". Or un draft tout juste généré doit être dirty jusqu'à la sauvegarde. Correction :

```js
function onTextareaChange() {
    if (state.isNew) {                // new prompts are always dirty until saved
        if (!state.isDirty) markDirty();
        return;
    }
    // ... existing logic
}
```

## Critères d'acceptation

| # | Test | Attendu |
|---|---|---|
| 1 | `GET /admin-lab` retourne 200 avec les nouveaux éléments (`btn-generate`, `modal-generate`, `gen-key`, `gen-pdfs`, `gen-truth`, `btn-gen-submit`) | Tous présents dans le DOM |
| 2 | Le template référence toujours `admin_lab.js` | OK |
| 3 | Le JS a les fonctions nouvelles (`submitGenerate`, `loadDraft`) et les IDs cohérents | Grep OK |
| 4 | Le JS n'a pas de syntaxe cassée (braces/parens balanced) | OK |
| 5 | `/admin` (stable) n'est PAS modifié (zero diff dans `templates/admin.html` et `static/js/admin.js`) | OK |
| 6 | Aucune régression sur `/admin`, `/admin-lab`, `/api/admin/prompts*` | Tous 200 |

Le vrai test fonctionnel (upload + OCR + génération) se fera manuellement dans un navigateur avec Ollama allumé.

## Hors scope

- 4.4 — Auto-test du prompt généré sur les mêmes échantillons
- Drag-drop zone (simple input file multiple suffit)
- Preview / re-génération en un clic
- Sauvegarde du dernier draft en brouillon local (localStorage) — YAGNI
