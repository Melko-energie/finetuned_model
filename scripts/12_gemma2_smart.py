"""
12_gemma2_smart.py — Extraction NER avec Gemma2:9b et prompts spécialisés par fournisseur.

Utilise le texte OCR DocTR existant (data/ocr_texts/) et des prompts adaptés
à chaque fournisseur pour maximiser la qualité d'extraction.
"""

import ollama
import json
import os
import re
import glob

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OCR_DIR = os.path.join(BASE_DIR, "data", "ocr_texts")
PDF_DIR = os.path.join(BASE_DIR, "data", "raw_pdfs")

# ─────────────────────────────────────────
# CHAMPS À EXTRAIRE (toujours les mêmes)
# ─────────────────────────────────────────

CHAMPS = [
    "NUMERO_FACTURE", "DATE_FACTURE", "MONTANT_HT", "TAUX_TVA", "MONTANT_TTC",
    "NOM_INSTALLATEUR", "COMMUNE_TRAVAUX", "CODE_POSTAL", "ADRESSE_TRAVAUX",
]

JSON_TEMPLATE = """{
  "NUMERO_FACTURE": "...",
  "DATE_FACTURE": "...",
  "MONTANT_HT": "...",
  "TAUX_TVA": "...",
  "MONTANT_TTC": "...",
  "NOM_INSTALLATEUR": "...",
  "COMMUNE_TRAVAUX": "...",
  "CODE_POSTAL": "...",
  "ADRESSE_TRAVAUX": "..."
}"""

# ─────────────────────────────────────────
# PROMPTS SPÉCIALISÉS PAR FOURNISSEUR
# ─────────────────────────────────────────

PROMPTS_INSTALLATEURS = {
    "a2m": {
        "detecter": ["a2m elec", "a2melec", "a2melecmahdi@sfr.fr", "433 763 059"],
        "prompt": f"""Tu es un extracteur de données de factures BTP. Voici le texte OCR d'une facture de A2M ELEC (électricien RGE QUALIFELEC, Amiens).

PARTICULARITÉS A2M :
- Numéro facture format "FA22-23" (FA + année 2 chiffres + tiret + séquence)
- TVA habituelle : 5,50% (travaux rénovation énergétique)
- Montants : cherche "MONTANT TOTAL HT", "TOTAL GENERAL" puis "TVA 5,50%" puis "TOTAL TTC a payer"
- Adresse travaux : cherche après "MARCHE" ou "BC No" l'adresse du chantier
- Installateur : A2M ELEC (EURL), 11 Avenue de la Paix, 80000 AMIENS

Extrais les champs suivants du texte OCR ci-dessous.
Si un champ n'est pas visible, mets null.
Réponds UNIQUEMENT en JSON valide, aucun texte avant ou après.
{JSON_TEMPLATE}

TEXTE OCR :
""",
    },
    "arcana": {
        "detecter": ["arcana", "arcana-architecture", "arcana architecture", "753 191 980"],
        "prompt": f"""Tu es un extracteur de données de factures BTP. Voici le texte OCR d'une NOTE D'HONORAIRES de ARCANA architecture (SARL d'Architecture, Amiens).

PARTICULARITÉS ARCANA :
- Document intitulé "NOTE D'HONORAIRES" (pas "Facture")
- Numéro format "ARCANA 2205864" (préfixe ARCANA + 7 chiffres)
- TVA : 20%
- Montants : tableau de phases (DIAG, AVP, PROJET, ACT, VISA, DET, AOR) avec avancement %. Cherche "Acompte demande HT" ou "TOTAL HT" puis "TVA 20%" puis "TTC"
- Installateur : ARCANA architecture, 52 rue de l'Amiral Courbet, 80000 Amiens

Extrais les champs suivants du texte OCR ci-dessous.
Si un champ n'est pas visible, mets null.
Réponds UNIQUEMENT en JSON valide, aucun texte avant ou après.
{JSON_TEMPLATE}

TEXTE OCR :
""",
    },
    "cailloce": {
        "detecter": ["cailloce", "cailloce-avocat", "pc@cailloce", "50328568600039"],
        "prompt": f"""Tu es un extracteur de données de factures BTP. Voici le texte OCR d'une facture de Pierre CAILLOCE Avocat (Paris).

PARTICULARITÉS CAILLOCE :
- Numéro facture format "2022 109" (année + espace + séquence)
- TVA : 20%
- Montants : facturation horaire simple. Cherche "HT", "TVA 20%", "Total a payer TTC"
- Installateur : PIERRE CAILLOCE - AVOCAT, 10 rue Thimonnier, 75009 Paris

Extrais les champs suivants du texte OCR ci-dessous.
Si un champ n'est pas visible, mets null.
Réponds UNIQUEMENT en JSON valide, aucun texte avant ou après.
{JSON_TEMPLATE}

TEXTE OCR :
""",
    },
    "dila": {
        "detecter": ["dila", "direction de l'information legale", "contentieux@dila", "130009186"],
        "prompt": f"""Tu es un extracteur de données de factures BTP. Voici le texte OCR d'un TITRE DE PERCEPTION de la DILA (Direction de l'information légale et administrative).

PARTICULARITÉS DILA :
- Document intitulé "Titre de perception" (pas "Facture")
- Numéro format "22-41537" il vient apres référence de l'avis
- TVA : 20%
- Montants : cherche "TOTAL DU" avec montant EUR, "TVA 20", puis total final
- Installateur : DILA, 26 rue Desaix, 75727 PARIS Cedex 15

Extrais les champs suivants du texte OCR ci-dessous.
Si un champ n'est pas visible, mets null.
Réponds UNIQUEMENT en JSON valide, aucun texte avant ou après.
{JSON_TEMPLATE}

TEXTE OCR :
""",
    },
    "eco2e": {
        "detecter": ["eco2e", "misiurny", "eco2e@misiurny", "509224127"],
        "prompt": f"""Tu es un extracteur de données de factures BTP. Voici le texte OCR d'une facture de ECO2E Bureau d'études Fluides (Dury).

PARTICULARITÉS ECO2E :
- Numéro facture : numérique simple (ex: "1688"), aussi ref interne "E22/12"
- TVA : 20%
- Montants : cherche "Total EUR HT", "Acompte a deduire", "T.V.A. 20%", "Total EUR TTC", "NET A PAYER"
- Installateur : ECO2E Bureau d'études Fluides Marc MISIURNY, 1 Allée de la pépinière, Centre Oasis, 80480 DURY

Extrais les champs suivants du texte OCR ci-dessous.
Si un champ n'est pas visible, mets null.
Réponds UNIQUEMENT en JSON valide, aucun texte avant ou après.
{JSON_TEMPLATE}

TEXTE OCR :
""",
    },
    "esteve": {
        "detecter": ["esteve", "esteve-electricite", "esteve electricite", "322 804 394"],
        "prompt": f"""Tu es un extracteur de données de factures BTP. Voici le texte OCR d'une facture de ESTEVE ELECTRICITE (Amiens).

PARTICULARITÉS ESTEVE :
- Numéro facture format "22/09/0333" (AA/MM/NNNN)
- DATE_FACTURE : uniquement la date d'émission de la facture. Ignorer date d'échéance.
- TVA : 20%
- Montants : ligne items puis "Base HT / Taux TVA / Montant TVA / Montant T.T.C." puis "TOTAL TTC", "ACOMPTE", "NET A PAYER"
- Installateur : ESTEVE ELECTRICITE (SARL), 51 Rue de Sully, 80000 AMIENS

Extrais les champs suivants du texte OCR ci-dessous.
Si un champ n'est pas visible, mets null.
Réponds UNIQUEMENT en JSON valide, aucun texte avant ou après.
{JSON_TEMPLATE}

TEXTE OCR :
""",
    },
    "exim": {
        "detecter": ["athos solutions", "exim", "controles mesures picardie", "49040021500029"],
        "prompt": f"""Tu es un extracteur de données de factures BTP. Voici le texte OCR d'une facture de EXIM / ATHOS Solutions Picardie (diagnostics amiante, Amiens).

PARTICULARITÉS EXIM :
- Numéro facture format "FA220727 47143" (FA + AAMMJJ BBCCD)
- TVA : 20%
- Montants : cherche "Total HT net", "Total TVA", "Total TTC net", "MONTANT A PAYER"
- Adresse travaux : chaque dossier a sa propre adresse d'intervention
- Installateur : ATHOS Solutions Picardie / EXIM, 30 avenue d'Italie, 80090 AMIENS

Extrais les champs suivants du texte OCR ci-dessous.
Si un champ n'est pas visible, mets null.
Réponds UNIQUEMENT en JSON valide, aucun texte avant ou après.
{JSON_TEMPLATE}

TEXTE OCR :
""",
    },
    "gazette": {
        "detecter": ["gazette", "gazette solutions", "gazettesolutions", "794 696 344"],
        "prompt": f"""Tu es un extracteur de données de factures BTP. Voici le texte OCR d'une facture de LA GAZETTE SOLUTIONS (annonces légales, Lille).

PARTICULARITÉS GAZETTE :
- Numéro facture format "22031090" (8 chiffres, basé date)
- TVA : 20%
- Montants : cherche "Total HT", "Montant TVA", "Net a payer"
- Adresse travaux : souvent dans les détails de l'annonce (département, commune)
- Installateur : LA GAZETTE SOLUTIONS (SARL), 7 RUE JACQUEMARS GIELEES, 59000 LILLE

Extrais les champs suivants du texte OCR ci-dessous.
Si un champ n'est pas visible, mets null.
Réponds UNIQUEMENT en JSON valide, aucun texte avant ou après.
{JSON_TEMPLATE}

TEXTE OCR :
""",
    },
    "gigabat": {
        "detecter": ["gigabat", "51284656900030"],
        "prompt": f"""Tu es un extracteur de données de factures BTP. Voici le texte OCR d'une facture de GIGABAT (coordination SPS, Amiens).

PARTICULARITÉS GIGABAT :
- Numéro facture format "FA220614 5233" (FA + AAMMJJ BBCC)
- TVA : 20%
- Montants : cherche "Total HT net", "Total TVA", "Total TTC net", "MONTANT A PAYER"
- Installateur : GIGABAT (SARL), 31 rue de la Hotoie, 80000 AMIENS

Extrais les champs suivants du texte OCR ci-dessous.
Si un champ n'est pas visible, mets null.
Réponds UNIQUEMENT en JSON valide, aucun texte avant ou après.
{JSON_TEMPLATE}

TEXTE OCR :
""",
    },
    "hestia": {
        "detecter": ["hestia", "hestia bureau", "hestia habitat"],
        "prompt": f"""Tu es un extracteur de données de factures BTP. Voici le texte OCR d'une facture de HESTIA Bureau d'Études Habitat (Paris).

PARTICULARITÉS HESTIA :
- Numéro facture format "2022-09-002" (AAAA-MM-NNN)
- TVA : 10% (taux rénovation)
- Montants : cherche "Montant des honoraires H.T.", "TVA a 10%", "Montant des honoraires T.T.C."
- Installateur : HESTIA Bureau d'Études Habitat, 11 rue Peclet, 75015 PARIS

Extrais les champs suivants du texte OCR ci-dessous.
Si un champ n'est pas visible, mets null.
Réponds UNIQUEMENT en JSON valide, aucun texte avant ou après.
{JSON_TEMPLATE}

TEXTE OCR :
""",
    },
    "kelvin": {
        "detecter": ["kelvin", "e.bougis@kelvin", "bougis"],
        "prompt": f"""Tu es un extracteur de données de factures BTP. Voici le texte OCR d'une facture de KELVIN (études thermiques, Boves).

PARTICULARITÉS KELVIN :
- Numéro facture format "FCKE22049" (FCKE + 5 chiffres)
- TVA : 20%
- Montants : cherche "MONTANT TOTAL H.T.", "T.V.A. 20%", "MONTANT TOTAL T.T.C."
- Installateur : KELVIN (EURL), 2Bis Place de L'Amiral Courbet, 80440 BOVES

Extrais les champs suivants du texte OCR ci-dessous.
Si un champ n'est pas visible, mets null.
Réponds UNIQUEMENT en JSON valide, aucun texte avant ou après.
{JSON_TEMPLATE}

TEXTE OCR :
""",
    },
    # ── NVINS : 8 sous-installateurs (auto-facturations SIP AMIENS) ──
    "nvins_klisz": {
        "detecter": ["klisz", "tatianaeurldk", "42446766000033"],
        "prompt": f"""Tu es un extracteur de données de factures BTP. Voici le texte OCR d'une auto-facturation émise par SIP AMIENS pour KLISZ (peinture/finitions, Albert).

PARTICULARITÉS KLISZ :
- Numéro facture format "8DE-120240031" (préfixe 8DE + année + séquence)
- TVA : 20%
- Montants : utilise le point comme séparateur décimal (pas virgule). Cherche "Total net HT", "Total TVA", "Total TTC", "Net a payer"
- Adresse travaux : cherche l'adresse d'exécution dans les lignes de détail
- Installateur : KLISZ (Artisan), 24 RUE DE L INDUSTRIE, 80300 ALBERT
- SIRET : 42446766000033 / NAF 4334Z

Extrais les champs suivants du texte OCR ci-dessous.
Si un champ n'est pas visible, mets null.
Réponds UNIQUEMENT en JSON valide, aucun texte avant ou après.
{JSON_TEMPLATE}

TEXTE OCR :
""",
    },
    "nvins_sip_amiens": {
        "detecter": ["sip amiens", "sip-amiens", "561720939"],
        "prompt": f"""Tu es un extracteur de données de factures BTP. Voici le texte OCR d'une auto-facturation émise par SIP AMIENS. Le vrai installateur est indiqué en en-tête de la facture.

PARTICULARITÉS SIP AMIENS :
- Numéro facture format "8DE-120240003" (préfixe 8XX + année + séquence)
- TVA : 20%
- Montants : cherche "Total net HT", "Total TVA", "Total TTC", "Net a payer". Séparateur décimal = point.
- NOM_INSTALLATEUR : le nom en GROS en haut de page (PAS "SIP AMIENS" qui est l'émetteur)
- Adresse travaux : cherche l'adresse d'exécution dans les lignes de détail
- SIP AMIENS : 13 PLACE D'AGUESSEAU, 80005 AMIENS CEDEX 1

Extrais les champs suivants du texte OCR ci-dessous.
Si un champ n'est pas visible, mets null.
Réponds UNIQUEMENT en JSON valide, aucun texte avant ou après.
{JSON_TEMPLATE}

TEXTE OCR :
""",
    },
    "nvins_proxiserve": {
        "detecter": ["proxiserve", "33487372601435", "cdanger@proxiserve"],
        "prompt": f"""Tu es un extracteur de données de factures BTP. Voici le texte OCR d'une auto-facturation émise par SIP AMIENS pour PROXISERVE (plomberie/chauffage, Levallois-Perret).

PARTICULARITÉS PROXISERVE :
- Numéro facture format "8PR-120240156" (préfixe 8PR + année + séquence)
- TVA : 5,50% (taux réduit rénovation énergétique)
- Montants : cherche "Total net HT", "Total TVA", "Total TTC", "Net a payer". Séparateur décimal = point.
- Adresse travaux : cherche l'adresse d'exécution dans les lignes de détail
- Installateur : PROXISERVE (SA), 155-159 RUE ANATOLE FRANCE, 92300 LEVALLOIS-PERRET
- SIRET : 33487372601435 / NAF 4322B

Extrais les champs suivants du texte OCR ci-dessous.
Si un champ n'est pas visible, mets null.
Réponds UNIQUEMENT en JSON valide, aucun texte avant ou après.
{JSON_TEMPLATE}

TEXTE OCR :
""",
    },
    "nvins_logista": {
        "detecter": ["logista", "39462912500748", "logistahometech"],
        "prompt": f"""Tu es un extracteur de données de factures BTP. Voici le texte OCR d'une auto-facturation émise par SIP AMIENS pour LOGISTA (plomberie/chauffage, Saint-Laurent-Blangy).

PARTICULARITÉS LOGISTA :
- Numéro facture format "8LO-120240014" (préfixe 8LO + année + séquence)
- TVA : 20%
- Montants : cherche "Total net HT", "Total TVA", "Total TTC", "Net a payer". Séparateur décimal = point.
- Adresse travaux : cherche l'adresse d'exécution dans les lignes de détail
- Installateur : LOGISTA (SAS), ZAC des Rosati, 110 Allée du Vélodrome, 62223 SAINT-LAURENT-BLANGY
- SIRET : 39462912500748 / NAF 4322B

Extrais les champs suivants du texte OCR ci-dessous.
Si un champ n'est pas visible, mets null.
Réponds UNIQUEMENT en JSON valide, aucun texte avant ou après.
{JSON_TEMPLATE}

TEXTE OCR :
""",
    },
    "nvins_lunion": {
        "detecter": ["l'union des peintres", "union des peintres", "55172041000028", "union.peintres"],
        "prompt": f"""Tu es un extracteur de données de factures BTP. Voici le texte OCR d'une auto-facturation émise par SIP AMIENS pour L'UNION DES PEINTRES (peinture, Amiens, SCOP).

PARTICULARITÉS L'UNION DES PEINTRES :
- Numéro facture format "8UN-120240232" (préfixe 8UN + année + séquence)
- TVA : 20%
- Montants : cherche "Total net HT", "Total TVA", "Total TTC", "Net a payer". Séparateur décimal = point.
- Adresse travaux : cherche l'adresse d'exécution dans les lignes de détail
- Installateur : L'UNION DES PEINTRES (SCOP SA), 21 rue de Sully, Espace 07, 80000 AMIENS
- SIRET : 55172041000028 / NAF 4334Z

Extrais les champs suivants du texte OCR ci-dessous.
Si un champ n'est pas visible, mets null.
Réponds UNIQUEMENT en JSON valide, aucun texte avant ou après.
{JSON_TEMPLATE}

TEXTE OCR :
""",
    },
    "nvins_sas_appli": {
        "detecter": ["sas appli", "appli.fr", "32011536300022", "pouillieute"],
        "prompt": f"""Tu es un extracteur de données de factures BTP. Voici le texte OCR d'une auto-facturation émise par SIP AMIENS pour SAS APPLI (peinture, Amiens).

PARTICULARITÉS SAS APPLI :
- Numéro facture format "8AP-120240008" (préfixe 8AP + année + séquence)
- TVA : 20%
- Montants : cherche "Total net HT", "Total TVA", "Total TTC", "Net a payer". Séparateur décimal = point.
- Adresse travaux : cherche l'adresse d'exécution dans les lignes de détail
- Installateur : SAS APPLI, ZI NORD, 3 RUE DE LA CROIX DE PIERRE, 80080 AMIENS
- SIRET : 32011536300022 / NAF 4334Z

Extrais les champs suivants du texte OCR ci-dessous.
Si un champ n'est pas visible, mets null.
Réponds UNIQUEMENT en JSON valide, aucun texte avant ou après.
{JSON_TEMPLATE}

TEXTE OCR :
""",
    },
    "nvins_techsol": {
        "detecter": ["techsol", "41111795500038", "sarl-lefebvre"],
        "prompt": f"""Tu es un extracteur de données de factures BTP. Voici le texte OCR d'une auto-facturation émise par SIP AMIENS pour TECHSOL (revêtements de sols, Hangest-en-Santerre).

PARTICULARITÉS TECHSOL :
- Numéro facture format "8TH-120240021" (préfixe 8TH + année + séquence)
- TVA : 20%
- Montants : cherche "Total net HT", "Total TVA", "Total TTC", "Net a payer". Séparateur décimal = point.
- Adresse travaux : cherche l'adresse d'exécution dans les lignes de détail
- Installateur : TECHSOL (SARL), ZA DU PETIT HANGEST, 80134 HANGEST EN SANTERRE
- SIRET : 41111795500038 / NAF 4333Z

Extrais les champs suivants du texte OCR ci-dessous.
Si un champ n'est pas visible, mets null.
Réponds UNIQUEMENT en JSON valide, aucun texte avant ou après.
{JSON_TEMPLATE}

TEXTE OCR :
""",
    },
    "nvins_numeriss": {
        "detecter": ["numeriss", "79086980400035", "contact@numeriss"],
        "prompt": f"""Tu es un extracteur de données de factures BTP. Voici le texte OCR d'une auto-facturation émise par SIP AMIENS pour NUMERISS (électricité, Poulainville).

PARTICULARITÉS NUMERISS :
- Numéro facture format "8NU-120240117" (préfixe 8NU + année + séquence)
- TVA : 20%
- Montants : cherche "Total net HT", "Total TVA", "Total TTC", "Net a payer". Séparateur décimal = point.
- Adresse travaux : cherche le "Programme" ou l'adresse d'exécution dans les lignes de détail
- Installateur : NUMERISS (SAS), 144 Rue Marius Morel, 80260 POULAINVILLE
- SIRET : 79086980400035 / NAF 4321A

Extrais les champs suivants du texte OCR ci-dessous.
Si un champ n'est pas visible, mets null.
Réponds UNIQUEMENT en JSON valide, aucun texte avant ou après.
{JSON_TEMPLATE}

TEXTE OCR :
""",
    },
     "orea": {
        "detecter": ["orea", "531 325 132"],
        "prompt": f"""Tu es un extracteur de données de factures BTP. Voici le texte OCR d'une NOTE D'HONORAIRES de OREA (maîtrise d'oeuvre, Dury).

PARTICULARITÉS OREA :
- Document intitulé "NOTE D'HONORAIRES"
- Numéro facture format "22097" cherche "Facture N'" suivi d'un numéro (5 chiffres)
- TVA : 20%
- Montants : tableau de phases (DIAG/ETUDES/ACT/VISA/DET/AOR). Cherche "MONTANT DE LA NOTE D'HONORAIRES", "T.V.A 20%", "MONTANT T.T.C DE LA NOTE D'HONORAIRES"
- Installateur : OREA (SARL), Place des Abies, Centre Oasis, 80480 DURY

Extrais les champs suivants du texte OCR ci-dessous.
Si un champ n'est pas visible, mets null.
Réponds UNIQUEMENT en JSON valide, aucun texte avant ou après.
{JSON_TEMPLATE}

TEXTE OCR :
""",
    },
    "poulain": {
        "detecter": ["poulain", "bet.poulain", "bet philippe poulain"],
        "prompt": f"""Tu es un extracteur de données de factures BTP. Voici le texte OCR d'une DEMANDE D'HONORAIRES de B.E.T. PHILIPPE POULAIN (études thermiques, Amiens).

PARTICULARITÉS POULAIN :
- Document intitulé "DEMANDE D'HONORAIRES"
- Numéro format "2129 - 702" (séquence - sous-numéro)
- TVA : 20%
- Montants : tableau de phases (DIAG/PLAN/ET) avec avancement. Cherche "CHT", "TVA", "CTTC" ou "Taux de TVA: 20%"
- MONTANT_HT : prendre UNIQUEMENT le dernier Total HT affiché. Ignorer acomptes et sous-totaux.
- Installateur : B.E.T. PHILIPPE POULAIN, 123 boulevard de Strasbourg, 80000 AMIENS

Extrais les champs suivants du texte OCR ci-dessous.
Si un champ n'est pas visible, mets null.
Réponds UNIQUEMENT en JSON valide, aucun texte avant ou après.
{JSON_TEMPLATE}

TEXTE OCR :
""",
    },
    "rcpi": {
        "detecter": ["rcpi", "rcpi.fr", "423 931 427", "maitre d'oeuvre batiment"],
        "prompt": f"""Tu es un extracteur de données de factures BTP. Voici le texte OCR d'une facture de RCPI Maître d'Oeuvre Bâtiment (Beauvais).

PARTICULARITÉS RCPI :
- Numéro facture format "GL 027-01-22" (préfixe + séquence-mois-année). Avoir : "AGL 001-03-22"
- TVA : 20%
- Montants : tableau de missions avec avancement %. Cherche "TOTAL HT", "TVA 20%", "TOTAL TTC"
- Installateur : RCPI (SARL), 1 rue de Pinconlieu, 60000 Beauvais

Extrais les champs suivants du texte OCR ci-dessous.
Si un champ n'est pas visible, mets null.
Réponds UNIQUEMENT en JSON valide, aucun texte avant ou après.
{JSON_TEMPLATE}

TEXTE OCR :
""",
    },
    "socotec": {
        "detecter": ["socotec", "construction.amiens@socotec", "83415751300922", "socotec construction"],
        "prompt": f"""Tu es un extracteur de données de factures BTP. Voici le texte OCR d'une facture/avoir de SOCOTEC Construction (contrôle technique).

PARTICULARITÉS SOCOTEC :
- Numéro format "2208000011/151V0" (AAMM + séquence / code affaire)
- TVA : 20%
- Montants : cherche "Total" avec HT / TVA / TTC en EUR, puis "A REGLER"
- Installateur : SOCOTEC Construction (SAS), agence 1 allée de la Pépinière, 80480 DURY

Extrais les champs suivants du texte OCR ci-dessous.
Si un champ n'est pas visible, mets null.
Réponds UNIQUEMENT en JSON valide, aucun texte avant ou après.
{JSON_TEMPLATE}

TEXTE OCR :
""",
    },
    "ternel": {
        "detecter": ["ternel", "ternelcouverture", "ternel couverture", "45009851200038"],
        "prompt": f"""Tu es un extracteur de données de factures BTP. Voici le texte OCR d'une facture de Ternel Couverture (charpente/zinguerie, Albert).

PARTICULARITÉS TERNEL :
- Numéro facture : 8 chiffres (ex: "00002810")
- TVA MIXTE : peut avoir 20% ET 5,5% sur la même facture. Indique les deux taux séparés par "/"
- Montants : récapitulatif en bas. Cherche "Total H.T.", "TVA1: 20%", "TVA2: 5,5%", "Total T.T.C.", "Net a payer"
- MONTANT_HT : prendre UNIQUEMENT le dernier Total HT affiché. Ignorer acomptes et sous-totaux.
- Installateur : Ternel Couverture, 8 rue de l'industrie, 80300 ALBERT

Extrais les champs suivants du texte OCR ci-dessous.
Si un champ n'est pas visible, mets null.
Pour TAUX_TVA avec taux multiples, indique "20% / 5.5%".
Réponds UNIQUEMENT en JSON valide, aucun texte avant ou après.
{JSON_TEMPLATE}

TEXTE OCR :
""",
    },
    "DEFAULT": {
        "detecter": [],
        "prompt": f"""Tu es un extracteur de données de factures BTP françaises. Voici le texte OCR d'une facture.

RÈGLES GÉNÉRALES :
- NUMERO_FACTURE : numéro complet après "N°", "Facture N°", "Réf", etc.
- DATE_FACTURE : format JJ/MM/AAAA
- MONTANT_HT : montant hors taxes. Cherche "Total HT", "Net HT", "Montant HT"
- TAUX_TVA : pourcentage TVA (ex: "20%", "10%", "5.5%")
- MONTANT_TTC : montant TTC. Cherche "Total TTC", "Net à payer"
- NOM_INSTALLATEUR : entreprise qui ÉMET la facture (pas le client)
- COMMUNE_TRAVAUX : ville du chantier
- CODE_POSTAL : code postal 5 chiffres du chantier
- ADRESSE_TRAVAUX : adresse complète du chantier

Si un champ n'est pas visible, mets null.
Réponds UNIQUEMENT en JSON valide, aucun texte avant ou après.
{JSON_TEMPLATE}

TEXTE OCR :
""",
    },
}


# ─────────────────────────────────────────
# DÉTECTION FOURNISSEUR
# ─────────────────────────────────────────

def detect_installateur(texte):
    """Détecte le fournisseur à partir du texte OCR en cherchant des mots-clés.

    Pour les factures nvins (auto-facturations SIP AMIENS), détection en 2 étapes :
    1. Détecter que c'est une auto-facturation SIP (mot-clé "auto-facturation")
    2. Identifier le vrai installateur parmi les 8 sous-fournisseurs nvins
    """
    texte_lower = texte.lower()

    # Étape 1 : détecter si c'est une auto-facturation SIP AMIENS
    is_autofact = ("auto-facturation" in texte_lower or "auto facturation" in texte_lower
                   or "autofacturation" in texte_lower)

    if is_autofact:
        # Étape 2 : chercher le vrai installateur parmi les nvins_*
        for nom, config in PROMPTS_INSTALLATEURS.items():
            if not nom.startswith("nvins_") or nom == "nvins_sip_amiens":
                continue
            for mot in config["detecter"]:
                if mot.lower() in texte_lower:
                    return nom
        # Fallback : SIP AMIENS générique
        return "nvins_sip_amiens"

    # Détection classique (hors nvins)
    for nom, config in PROMPTS_INSTALLATEURS.items():
        if nom == "DEFAULT" or nom.startswith("nvins_"):
            continue
        for mot in config["detecter"]:
            if mot.lower() in texte_lower:
                return nom

    # Dernier recours : tester aussi les nvins_* (au cas où pas de mention "auto-facturation")
    for nom, config in PROMPTS_INSTALLATEURS.items():
        if not nom.startswith("nvins_"):
            continue
        for mot in config["detecter"]:
            if mot.lower() in texte_lower:
                return nom

    return "DEFAULT"


# ─────────────────────────────────────────
# LECTURE OCR
# ─────────────────────────────────────────

def get_ocr_text(pdf_path):
    """Cherche le JSON OCR correspondant au PDF et reconstruit le texte trié par position Y."""
    pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]

    # Chercher le fichier JSON dans tous les sous-dossiers de ocr_texts/
    json_path = None
    for supplier_dir in os.listdir(OCR_DIR):
        supplier_path = os.path.join(OCR_DIR, supplier_dir)
        if not os.path.isdir(supplier_path):
            continue
        for f in os.listdir(supplier_path):
            if f.endswith(".json"):
                # Match par nom de base du PDF (sans extension)
                f_base = os.path.splitext(f)[0]
                if pdf_name.upper() in f_base.upper() or f_base.upper() in pdf_name.upper():
                    json_path = os.path.join(supplier_path, f)
                    break
            if json_path:
                break
        if json_path:
            break

    if not json_path:
        # Fallback : chercher par glob
        pattern = os.path.join(OCR_DIR, "**", f"*{pdf_name}*")
        matches = glob.glob(pattern, recursive=True)
        json_matches = [m for m in matches if m.endswith(".json")]
        if json_matches:
            json_path = json_matches[0]

    if not json_path:
        print(f"  ERREUR: Pas de JSON OCR trouvé pour {pdf_name}")
        return None

    print(f"  OCR trouvé : {os.path.relpath(json_path, BASE_DIR)}")

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Reconstruire le texte à partir de toutes les pages, trié par Y puis X
    all_tokens = []
    for page_idx, page_tokens in enumerate(data["pages"]):
        for token in page_tokens:
            bbox = token.get("bbox", [0, 0, 0, 0])
            all_tokens.append({
                "text": token["text"],
                "y": bbox[1],  # position Y (haut du token)
                "x": bbox[0],  # position X (gauche du token)
                "page": page_idx,
            })

    # Trier par page, puis par Y (lignes), puis par X (colonnes)
    # Regrouper par lignes approximatives (tolérance Y de 5 pixels)
    all_tokens.sort(key=lambda t: (t["page"], t["y"], t["x"]))

    lines = []
    current_line = []
    current_y = -999
    current_page = -1

    for token in all_tokens:
        if token["page"] != current_page or abs(token["y"] - current_y) > 5:
            if current_line:
                lines.append(" ".join(t["text"] for t in current_line))
            current_line = [token]
            current_y = token["y"]
            current_page = token["page"]
        else:
            current_line.append(token)

    if current_line:
        lines.append(" ".join(t["text"] for t in current_line))

    texte = "\n".join(lines)
    print(f"  Texte reconstruit : {len(lines)} lignes, {len(texte)} caractères")
    return texte


# ─────────────────────────────────────────
# NETTOYAGE JSON
# ─────────────────────────────────────────

def clean_json(raw):
    """Nettoie les balises markdown autour du JSON."""
    raw = raw.strip()
    if "```json" in raw:
        raw = raw.split("```json")[1].split("```")[0].strip()
    elif "```" in raw:
        raw = raw.split("```")[1].split("```")[0].strip()
    return raw


# ─────────────────────────────────────────
# EXTRACTION VIA GEMMA2
# ─────────────────────────────────────────

def extraire_champs(texte, installateur):
    """Appelle Gemma2:9b avec le prompt spécialisé du fournisseur détecté."""
    config = PROMPTS_INSTALLATEURS.get(installateur, PROMPTS_INSTALLATEURS["DEFAULT"])
    prompt = config["prompt"] + texte

    print(f"  Appel Gemma2:9b (prompt: {installateur})...")

    response = ollama.chat(
        model="gemma2:9b",
        messages=[{"role": "user", "content": prompt}],
        options={"temperature": 0, "seed": 42},
    )

    raw = clean_json(response["message"]["content"])

    try:
        result = json.loads(raw)
        return result
    except json.JSONDecodeError as e:
        print(f"  ERREUR JSON : {e}")
        print(f"  RAW : {raw[:500]}")
        return {champ: None for champ in CHAMPS}


# ─────────────────────────────────────────
# PIPELINE
# ─────────────────────────────────────────

def pipeline(pdf_path):
    """Pipeline complet : OCR → détection fournisseur → extraction."""
    print(f"\n{'='*60}")
    print(f"Facture : {os.path.basename(pdf_path)}")

    texte = get_ocr_text(pdf_path)
    if texte is None:
        return None, "ERREUR"

    installateur = detect_installateur(texte)
    print(f"  Fournisseur détecté : {installateur}")

    result = extraire_champs(texte, installateur)

    return result, installateur


# ─────────────────────────────────────────
# MAIN — Test sur 3 fournisseurs différents
# ─────────────────────────────────────────

if __name__ == "__main__":
    print("=== GEMMA2:9b SMART — Prompts spécialisés par fournisseur ===\n")

    # 3 PDFs de fournisseurs différents pour tester
    test_pdfs = [
        os.path.join(PDF_DIR, "a2m", "S1120630_MICROLAD-22AAC00000.PDF"),
        os.path.join(PDF_DIR, "esteve", "S1120318_MICROLAD-22A4924000.PDF"),
        os.path.join(PDF_DIR, "ternel", "S1120317_MICROLAD-22A4925000.PDF"),
    ]

    results = []
    success = 0

    for pdf_path in test_pdfs:
        if not os.path.exists(pdf_path):
            print(f"\n  SKIP: {pdf_path} introuvable")
            continue

        result, installateur = pipeline(pdf_path)

        if result:
            success += 1
            print(f"  Prompt utilisé : {installateur}")
            print(f"  Résultat :")
            for k, v in result.items():
                status = "ok" if v and v != "null" and str(v).lower() != "null" else "--"
                print(f"     [{status}] {k}: {v}")
            results.append({
                "facture": os.path.basename(pdf_path),
                "installateur_detecte": installateur,
                "extraction": result,
            })
        else:
            print(f"  Extraction échouée")

    # Résumé
    print(f"\n{'='*60}")
    print(f"Résumé : {success}/{len(test_pdfs)} factures extraites")

    total_champs = 0
    champs_trouves = 0
    for r in results:
        for v in r["extraction"].values():
            total_champs += 1
            if v and str(v).lower() != "null":
                champs_trouves += 1

    if total_champs > 0:
        pct = round(champs_trouves / total_champs * 100)
        print(f"Champs non-null : {champs_trouves}/{total_champs} ({pct}%)")

    # Sauvegarde
    output_path = os.path.join(BASE_DIR, "data", "test_gemma2_smart_results.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"Résultats sauvegardés : {output_path}")
