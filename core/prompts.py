"""Per-supplier prompt definitions used by core.detection and core.extraction."""

from core.config import JSON_TEMPLATE


PROMPT_TEXTE = """Tu es un expert comptable specialise dans les factures BTP francaises.

REGLES :
- NUMERO_FACTURE : numero COMPLET apres "N", "Facture N", "Ref". Garde tous les caracteres.
- DATE_FACTURE : format JJ/MM/AAAA.
- MONTANT_HT : montant AVANT TVA. Format "358.83". Cherche "Total HT", "Net HT".
- TAUX_TVA : uniquement le pourcentage. Exemple "20%".
- MONTANT_TTC : montant FINAL avec TVA. Cherche "Total TTC", "Net a payer".
- NOM_INSTALLATEUR : nom COMPLET de l'entreprise emettrice (pas le client).
- COMMUNE_TRAVAUX : ville du chantier.
- CODE_POSTAL : code postal a 5 chiffres.
- ADRESSE_TRAVAUX : adresse complete du chantier.

TEXTE DE LA FACTURE :
{texte}

Reponds UNIQUEMENT en JSON valide. Aucun texte avant ou apres.
{{"NUMERO_FACTURE":null,"DATE_FACTURE":null,"MONTANT_HT":null,"TAUX_TVA":null,"MONTANT_TTC":null,"NOM_INSTALLATEUR":null,"COMMUNE_TRAVAUX":null,"CODE_POSTAL":null,"ADRESSE_TRAVAUX":null}}"""


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
        "detecter": ["arcana", "arcana-architecture", "arcana architecture", "753 191 980", "753191980"],
        "prompt": f"""Tu es un extracteur de données de factures BTP. Voici le texte OCR d'une NOTE D'HONORAIRES de ARCANA architecture (SARL d'Architecture, maîtrise d'œuvre, Amiens).

PARTICULARITÉS ARCANA :
- Document intitulé "NOTE D'HONORAIRES" (pas "Facture").
- NUMERO_FACTURE : après "No ARCANA" (préfixe ARCANA + 7-8 chiffres, ex: "ARCANA 2205864", "ARCANA 23101051", "ARCANA 2212924"). Garder le préfixe "ARCANA" dans le numéro.
- DATE_FACTURE : dans la ligne "Amiens le DD Mois AAAA" (ex: "Amiens le 18 Mai 2022" → "18/05/2022", "Amiens le 14 Décembre 2022" → "14/12/2022"). Convertir le mois en chiffre. Format JJ/MM/AAAA.
- MONTANT_HT : prendre "Acompte demandé HT" (PAS "TOTAL HT" qui est le montant global du marché, pas de cette note). Séparateur décimal = virgule → convertir en point (ex: "5450,97" → "5450.97").
- TAUX_TVA : toujours "20%" (l'OCR peut garbler "20%" en "12%" ou autre — ignorer, c'est toujours 20%).
- MONTANT_TTC : après "TTC" (ex: "6541,16" → "6541.16"). Virgule → point.
- NOM_INSTALLATEUR : toujours "ARCANA".
- ADRESSE_TRAVAUX : dans la ligne de description du marché après "MARCHE DE MAITRISE D'ŒUVRE -" ou "CONCEPTION REALISATION". Cette ligne contient la COMMUNE suivie de la RUE ou du QUARTIER puis la description des travaux. Extraire UNIQUEMENT la partie adresse (rue/quartier). Exemples :
  * "AMIENS RUE BERANGER Transformation d'un bâtiment..." → ADRESSE_TRAVAUX = "RUE BERANGER"
  * "AMIENS REHABILITATION ETOUVIE BAT E" → ADRESSE_TRAVAUX = "ETOUVIE" (quartier)
- COMMUNE_TRAVAUX : premier mot(s) de la ligne de description du marché = la commune (souvent "AMIENS"). NE PAS prendre "AMIENS CEDEX" du client SIP.
- CODE_POSTAL : souvent absent dans les notes ARCANA. Mettre null si non visible.
IGNORER ABSOLUMENT :
  * Adresse client SIP : "13 PLACE D'AGUESSEAU", "80005 AMIENS CEDEX" — siège social, pas un chantier.
  * Adresse ARCANA : "52 rue de l'Amiral Courbet", "80000 Amiens" — c'est l'architecte.
  * Codes "BC 2023 ...", "2290/50" — références internes, pas des numéros de facture.
- SIRET : 753 191 980 / SARL d'Architecture

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
- ADRESSE_TRAVAUX : après "Adresse d'exécution ou de la livraison :" prendre UNIQUEMENT la/les lignes d'adresse (numéro + rue). IGNORER ABSOLUMENT les lignes "Logement :", "Bâtiment :", "Société :", "Programme :" ET tout ce qui vient APRÈS les labels "Marché n°:", "Engagement n°:", "Ref. fourn.:", "Ref. interne:" sur la même ligne (colonne voisine à droite).
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
- ADRESSE_TRAVAUX : après "Adresse d'exécution ou de la livraison :" prendre UNIQUEMENT la/les lignes d'adresse (numéro + rue). IGNORER ABSOLUMENT les lignes "Logement :", "Bâtiment :", "Société :", "Programme :" ET tout ce qui vient APRÈS les labels "Marché n°:", "Engagement n°:", "Ref. fourn.:", "Ref. interne:" sur la même ligne (colonne voisine à droite).
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
- Numéro facture format "8PR-120230142" (préfixe 8PR + année + séquence). Cherche après "Facture N°:" ou "Facture No:".
- DATE_FACTURE : date après "Date facture:". Format JJ/MM/AAAA. IGNORER la date d'exécution et la date d'échéance.
- TVA : soit 5,50% (travaux rénovation énergétique) soit 20,00% (travaux standard). Lire le taux exact dans la colonne "Tx TVA" ou la ligne "Taux".
- Montants : séparateur décimal = point. Cherche dans le bloc récapitulatif en bas à droite :
  * MONTANT_HT = "Total net HT" (PAS "Total HT" seul, prendre "Total net HT")
  * MONTANT_TTC = "Total TTC" ou "Net à payer" (les deux sont identiques)
  * Ignorer "Réduction globale" et "Frais divers" (toujours à "-")
- ADRESSE_TRAVAUX : après "Adresse d'exécution ou de la livraison :" prendre UNIQUEMENT la/les lignes d'adresse (numéro + rue). IGNORER ABSOLUMENT les lignes "Logement :", "Bâtiment :", "Société :", "Programme :" ET tout ce qui vient APRÈS les labels "Marché n°:", "Engagement n°:", "Ref. fourn.:", "Ref. interne:" sur la même ligne — ce sont des colonnes voisines à droite, pas l'adresse. Exemple : "2 RUE JEAN MONET Engagement n°: BT 2024 5542" → garder uniquement "2 RUE JEAN MONET".
- COMMUNE_TRAVAUX : ville sur la ligne avec le code postal (ex: "80300 ALBERT" → ALBERT)
- CODE_POSTAL : code postal 5 chiffres sur la même ligne que la commune (ex: "80300")
- NOM_INSTALLATEUR : toujours "PROXISERVE". C'est le fournisseur, PAS "SIP AMIENS" qui est l'émetteur de l'auto-facturation.
- SIRET : 33487372601435 / NAF 4322B

Extrais les champs suivants du texte OCR ci-dessous.
Si un champ n'est pas visible, mets null.
Réponds UNIQUEMENT en JSON valide, aucun texte avant ou après.
{JSON_TEMPLATE}

TEXTE OCR :
""",
    },
    "logista": {
        "detecter": ["logista hometech", "logista\nhometech", "remplacement chaudiere", "remplacement accumulateur", "detail de la prestation"],
        "prompt": f"""Tu es un extracteur de données de factures BTP. Voici le texte OCR d'une facture directe de LOGISTA HOMETECH (plomberie/chauffage/remplacement chaudières et accumulateurs).

PARTICULARITÉS LOGISTA (facture directe) :
- Numéro facture format "AM 23/05/0041" ou "AV 23/02/0033" (préfixe AM ou AV + AA/MM/NNNN). Cherche après "N°" en haut à droite.
- DATE_FACTURE : date après "DATE :" en haut à droite. Format JJ/MM/AAAA.
- TVA : soit 5,50% soit 20,00%. Lire le taux exact sur la ligne "Montant TVA X %".
- Montants : cherche dans le bloc récapitulatif à droite :
  * MONTANT_HT = "TOTAL HT"
  * MONTANT_TTC = "TOTAL TTC" ou "A REGLER" (les deux sont identiques)
- ADRESSE_TRAVAUX : deux mises en page possibles.
  (a) Bloc "Adresse d'intervention:" en haut (UNE seule adresse). L'OCR fusionne malheureusement 2 COLONNES côte à côte sur les mêmes lignes : COLONNE GAUCHE = adresse du CHANTIER (à garder), COLONNE DROITE = adresse du CLIENT SIP (à IGNORER). Extraire UNIQUEMENT les parties chantier (rue + résidence) en ignorant tout ce qui concerne le client.
  (b) Bloc "DETAIL DE LA PRESTATION" (PLUSIEURS adresses). Chaque bloc commence par un code logement (ex: "PACLOSL013", "2BERN3L019"). Concatène TOUTES les adresses séparées par " | ". Format : "RUE, CP VILLE" (ex: "13 RUE LE CLOS FORESTEL, 60120 PAILLART | 3 PARC DE BERNY, 80000 AMIENS").
  IGNORER ABSOLUMENT :
    * Adresse CLIENT SIP (colonne droite) : "SOCIETE IMMOBILIERE PICARDE", "SIP", "13 PLACE D'AGUESSEAU" / "13 PLACE D, AGUESSEAU", "BP 511", "80005 AMIENS", "CEDEX 1", "Code Logement : HLxxxxx", "Appt :".
    * Adresses d'AGENCE LOGISTA en bas de page : "7 ALLEE DU VIEUX BERGER", "110 ALLEE DU VELODROME", "37 RUE RENE DINGEON", "ZI RENE DINGEON", "ZAC DES ROSATI", "SAINT LAURENT BLANGY", "SAINT SAUVEUR", "ABBEVILLE".
  EXEMPLE (layout a) — OCR fusionné : "13 PLACE D, AGUESSEAU / FRISE LINSEY BP 511 / CEDEX 1 / 8F RUE PASTEUR 80005 AMIENS / RESIDENCE DES JONQUILLES / 80490 HALLENCOURT" → ADRESSE_TRAVAUX = "FRISE LINSEY 8 RUE PASTEUR RESIDENCE DES JONQUILLES" (retirer "13 PLACE D'AGUESSEAU", "BP 511", "CEDEX 1", "80005 AMIENS" qui sont le client SIP).
- COMMUNE_TRAVAUX : commune(s) du/des chantier(s) séparées par " | " si layout (b). IGNORER "AMIENS" associé à "80005" (client SIP), "SAINT LAURENT BLANGY", "SAINT SAUVEUR", "ABBEVILLE" (agences LOGISTA). Sur l'exemple ci-dessus → "HALLENCOURT".
- CODE_POSTAL : code(s) postal(aux) du/des chantier(s) séparé(s) par " | " si layout (b). IGNORER "80005" (client SIP), "62223", "80470", "80100" (agences LOGISTA). Sur l'exemple ci-dessus → "80490".
- NOM_INSTALLATEUR : toujours "LOGISTA HOMETECH".
- SIRET : 39462912500748 / NAF 4322B

Extrais les champs suivants du texte OCR ci-dessous.
Si un champ n'est pas visible, mets null.
Réponds UNIQUEMENT en JSON valide, aucun texte avant ou après.
{JSON_TEMPLATE}

TEXTE OCR :
""",
    },
    "nvins_logista": {
        "detecter": ["39462912500748", "logistahometech", "rat@logistahometech"],
        "prompt": f"""Tu es un extracteur de données de factures BTP. Voici le texte OCR d'une auto-facturation émise par SIP AMIENS pour LOGISTA (plomberie/chauffage, Saint-Laurent-Blangy).

PARTICULARITÉS LOGISTA :
- Numéro facture format "8LO-120230039" (préfixe 8LO + année + séquence). Cherche après "Facture N°:" ou "Facture No:".
- DATE_FACTURE : date après "Date facture:". Format JJ/MM/AAAA. IGNORER la date d'exécution et la date d'échéance.
- TVA : soit 5,50% (rénovation énergétique) soit 10,00% (travaux rénovation) soit 20,00% (travaux standard). Lire le taux exact dans la colonne "Tx TVA" ou la ligne "Taux".
- Montants : séparateur décimal = point. Cherche dans le bloc récapitulatif en bas à droite :
  * MONTANT_HT = "Total net HT" (PAS "Total HT" seul, prendre "Total net HT")
  * MONTANT_TTC = "Total TTC" ou "Net à payer" (les deux sont identiques)
  * Ignorer "Réduction globale" et "Frais divers" (toujours à "-")
- ADRESSE_TRAVAUX : après "Adresse d'exécution ou de la livraison :" prendre UNIQUEMENT la/les lignes d'adresse (numéro + rue). IGNORER ABSOLUMENT les lignes "Logement :", "Bâtiment :", "Société :", "Programme :" ET tout ce qui vient APRÈS les labels "Marché n°:", "Engagement n°:", "Ref. fourn.:", "Ref. interne:" sur la même ligne — ce sont des colonnes voisines à droite, pas l'adresse. Exemple : "2 RUE JEAN MONET Engagement n°: BT 2024 5542" → garder uniquement "2 RUE JEAN MONET".
- COMMUNE_TRAVAUX : ville sur la ligne avec le code postal (ex: "80500 MONTDIDIER" → MONTDIDIER). Si la ville contient "(le)" ou "(la)", garder uniquement le nom (ex: "CROTOY (le)" → "LE CROTOY").
- CODE_POSTAL : code postal 5 chiffres sur la même ligne que la commune
- NOM_INSTALLATEUR : toujours "LOGISTA". C'est le fournisseur, PAS "SIP AMIENS" qui est l'émetteur de l'auto-facturation.
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
- ADRESSE_TRAVAUX : après "Adresse d'exécution ou de la livraison :" prendre UNIQUEMENT la/les lignes d'adresse (numéro + rue). IGNORER ABSOLUMENT les lignes "Logement :", "Bâtiment :", "Société :", "Programme :" ET tout ce qui vient APRÈS les labels "Marché n°:", "Engagement n°:", "Ref. fourn.:", "Ref. interne:" sur la même ligne (colonne voisine à droite).
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
- ADRESSE_TRAVAUX : après "Adresse d'exécution ou de la livraison :" prendre UNIQUEMENT la/les lignes d'adresse (numéro + rue). IGNORER ABSOLUMENT les lignes "Logement :", "Bâtiment :", "Société :", "Programme :" ET tout ce qui vient APRÈS les labels "Marché n°:", "Engagement n°:", "Ref. fourn.:", "Ref. interne:" sur la même ligne (colonne voisine à droite).
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
- ADRESSE_TRAVAUX : après "Adresse d'exécution ou de la livraison :" prendre UNIQUEMENT la/les lignes d'adresse (numéro + rue). IGNORER ABSOLUMENT les lignes "Logement :", "Bâtiment :", "Société :", "Programme :" ET tout ce qui vient APRÈS les labels "Marché n°:", "Engagement n°:", "Ref. fourn.:", "Ref. interne:" sur la même ligne (colonne voisine à droite).
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
- ADRESSE_TRAVAUX : après "Adresse d'exécution ou de la livraison :" prendre UNIQUEMENT la/les lignes d'adresse (numéro + rue). IGNORER ABSOLUMENT les lignes "Logement :", "Bâtiment :", "Société :", "Programme :" ET tout ce qui vient APRÈS les labels "Marché n°:", "Engagement n°:", "Ref. fourn.:", "Ref. interne:" sur la même ligne (colonne voisine à droite).
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
        "detecter": ["bet poulain", "bet.poulain", "bet philippe poulain", "b.e.t. philippe poulain", "b.e.t. poulain"],
        "prompt": f"""Tu es un extracteur de données de factures BTP. Voici le texte OCR d'une DEMANDE D'HONORAIRES de B.E.T. PHILIPPE POULAIN (études thermiques, Amiens).

PARTICULARITÉS POULAIN :
- Document intitulé "DEMANDE D'HONORAIRES"
- Numéro format "2129 - 702" (séquence - sous-numéro)
- TVA : 20%
- Montants : tableau de phases (DIAG/PLAN/ET) avec avancement. Cherche "€ HT", "TVA", "€ TTC" ou "Taux de TVA: 20%"
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
- Numéro facture format "GL XXX-XX-XX" (ex: "GL 027-01-22"). Le préfixe "GL" est OBLIGATOIRE. Avoir : "AGL 001-03-22"
- TVA : 20%
- Installateur : RCPI (SARL), 1 rue de Pinconlieu, 60000 Beauvais
- DATE_FACTURE : chercher UNIQUEMENT la date après "Beauvais" (ex: "Beauvais, le 30 septembre 2022" → "30/09/2022"). Convertir en format JJ/MM/AAAA. IGNORER toute autre date du document.

MONTANT_HT :
- Cherche UNIQUEMENT le montant à côté de "TOTAL HT" (pas "Sous-total")
- PRIORITÉ : "TOTAL HT" > tout autre montant HT
- IGNORER ABSOLUMENT : "Sous-total HT", "Sous-total HT/cumul", "Sous-total HT déjà facturé"
- IGNORER : montants partiels, acomptes, avances, lignes de détail
- Si "Sous-total HT/cumul" = 4500 et "TOTAL HT" = 2250, la réponse est 2250
- Format : nombre seul sans € ni espaces (ex: "3409.00" pas "3 409,00 €")

MONTANT_TTC :
- Cherche "Net à payer", "TOTAL TTC", "Total TTC"
- Le TTC doit toujours être SUPÉRIEUR au HT. Si le montant trouvé est inférieur au HT → mettre null
- IGNORER "TOTAL TTC déjà facturé" et les restes à payer
- Format : nombre seul sans € ni espaces

VALIDATION OBLIGATOIRE :
- MONTANT_TTC doit être = MONTANT_HT × (1 + TAUX_TVA/100)
- Si TVA = 20% alors TTC = HT × 1.20
- Si le calcul ne correspond pas, cherche d'autres valeurs dans le texte
- Ne retourne jamais un TTC < HT

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
- ADRESSE_TRAVAUX / COMMUNE_TRAVAUX / CODE_POSTAL : chercher dans le bloc "Adresses de visite liées aux lignes de facture" (souvent en page 2, libellé parfois garblé par l'OCR en "Adressesdecsitoleeseuglgnesdolecturo" ou "Reutfonsléesauslignesdolactures"). Juste en-dessous, la ligne commence par un numéro d'ordre puis le nom du client ("SOCIETE IMMOBILIERE PICARDE D'HLM -LOGEMENT") suivi de la VRAIE adresse d'intervention (ex: "15 RUE LEMERCHIER") puis "CP COMMUNE" (ex: "80000 AMIENS France").
  IGNORER ABSOLUMENT :
    * Adresse client / facturation en haut : "13 PL D'AGUESSEAU", "131 PL D'AGUESSEAU", "80000 AMIENS" associé au client — c'est le SIÈGE SIP, JAMAIS un chantier.
    * Adresse agence SOCOTEC : "1 allée de la Pépinière", "Centre Oasis La Passiflore", "80480 DURY".
    * Siège SOCOTEC : "5 place des Frères Montgolfier", "CS 20732", "Guyancourt", "78182", "Saint-Quentin-en-Yvelines".
  Si plusieurs adresses de visite sont listées, concaténer ADRESSE_TRAVAUX / COMMUNE_TRAVAUX / CODE_POSTAL séparés par " | ".

Extrais les champs suivants du texte OCR ci-dessous.
Si un champ n'est pas visible, mets null.
Réponds UNIQUEMENT en JSON valide, aucun texte avant ou après.
{JSON_TEMPLATE}

TEXTE OCR :
""",
    },
    "jla": {
        "detecter": ["sarl j.l.a", "sarl jla", "j.l.a", "cboisdanghein@sfr", "88883273000012"],
        "prompt": f"""Tu es un extracteur de données de factures BTP. Voici le texte OCR d'une facture de SARL J.L.A (rénovation/bâtiment, Saint-Sauveur).

PARTICULARITÉS J.L.A :
- NUMERO_FACTURE : après "Référence :" (format 8 chiffres, ex: "00000232", "00000302").
- DATE_FACTURE : dans la ligne "SAINT SAUVEUR, le DD mois AAAA" (ex: "SAINT SAUVEUR, le 04 octobre 2022" → "04/10/2022"). Format JJ/MM/AAAA.
- MONTANT_HT : après "Total H.T." en bas de page (dernière page si multi-pages). Attention : séparateur de milliers = espace (ex: "1 776,00" → "1776.00"). Séparateur décimal = virgule → convertir en point.
- TAUX_TVA : après "Total T.V.A." (ex: "20,00 %" → "20%").
- MONTANT_TTC : après "Net à payer (Euros)" (ex: "2 131,20" → "2131.20"). Même règle : espace = milliers, virgule = décimal → convertir en point.
- NOM_INSTALLATEUR : toujours "SARL J.L.A".
- ADRESSE_TRAVAUX : dans la ligne "Objet :" qui contient la description des travaux ET l'adresse du chantier. Extraire UNIQUEMENT la partie adresse (rue + commune). IGNORER la description des travaux et le code "BT AAAA NNNN" (bon de travaux) en fin de ligne.
  Exemples :
  * "REPRISE DES TAPIS DE SOL PLACE DE LA LOGETTE A CORBIE BT 2022 6744" → ADRESSE_TRAVAUX = "PLACE DE LA LOGETTE", COMMUNE = "CORBIE"
  * "TRAVAUX D'ISOLATION CHANTIER SITUE RUE DES 17 COQUELICOTS A FRIVILLE ESCARBOTIN BT 2023 1760" → ADRESSE_TRAVAUX = "RUE DES 17 COQUELICOTS", COMMUNE = "FRIVILLE ESCARBOTIN"
- COMMUNE_TRAVAUX : la ville après la dernière occurrence de "A" ou "À" dans la ligne Objet (avant "BT"). Voir exemples ci-dessus.
- CODE_POSTAL : souvent absent dans la facture J.L.A. Mettre null si non visible.
IGNORER ABSOLUMENT :
  * Adresse J.L.A : "635 Rue Maurice Thorez", "80470 SAINT SAUVEUR" — c'est l'entreprise.
  * Adresse client SIP : "13 PLACE D'AGUESSEAU", "80000 AMIENS" — c'est le siège social SIP (blacklisté).
- SIRET : 88883273000012 / APE 4120A

Extrais les champs suivants du texte OCR ci-dessous.
Si un champ n'est pas visible, mets null.
Réponds UNIQUEMENT en JSON valide, aucun texte avant ou après.
{JSON_TEMPLATE}

TEXTE OCR :
""",
    },
    "clorofil": {
        "detecter": ["cloro'fil", "clorofil", "cloro fil", "clorofilconcept", "contact@clorofilconcept", "49155447300034", "491 554 473"],
        "prompt": f"""Tu es un extracteur de données de factures. Voici le texte OCR d'une facture de CLORO'FIL Concept (fourniture de linge / textiles, Bully 69210).

PARTICULARITÉS CLORO'FIL :
- NUMERO_FACTURE : après "FACTURE No" (format FC + 6 chiffres, ex: "FC220245", "FC230576").
- DATE_FACTURE : après "du" dans "FACTURE No ... du JJ/MM/AAAA" (ex: "du 03/03/2022" → "03/03/2022"). Déjà au format JJ/MM/AAAA.
- MONTANT_HT : après "Total HT" (dernière page si multi-pages). Séparateur de milliers = espace, décimal = virgule → convertir en point (ex: "21 809,65" → "21809.65", "1 892,85" → "1892.85"). NE PAS prendre "Base HT" (qui peut être un sous-total partiel).
- TAUX_TVA : après "Taux TVA" (ex: "20,00 %" → "20%").
- MONTANT_TTC : après "Total TTC" ou "Total à payer" (ex: "26 171,58" → "26171.58"). Même conversion.
- NOM_INSTALLATEUR : toujours "CLORO'FIL CONCEPT".
- ADRESSE_TRAVAUX : dans la section "Adresse de livraison:" (ex: "Tour St Michel"). Prendre le nom du bâtiment ou de la rue. IGNORER "BP 60" / "BP60" (boîte postale).
- COMMUNE_TRAVAUX : commune de livraison (ex: "TREGUIER").
- CODE_POSTAL : code postal de livraison (ex: "22220").
IGNORER ABSOLUMENT :
  * Adresse CLORO'FIL : "ZA La Plagne", "154 allée des Merisiers", "69210 BULLY" — c'est le fournisseur.
  * Adresse BPI FRANCE : "27-31 avenue du Général Leclerc", "94710 MAISON ALFORT CEDEX" — c'est la banque.
- SIRET : 49155447300034 / RCS Lyon / APE non spécifié

Extrais les champs suivants du texte OCR ci-dessous.
Si un champ n'est pas visible, mets null.
Réponds UNIQUEMENT en JSON valide, aucun texte avant ou après.
{JSON_TEMPLATE}

TEXTE OCR :
""",
    },
    "gaz_de_bordeaux": {
        "detecter": ["gaz de bordeaux", "gazdebordeaux", "axans@gazdebordeaux", "50294147900011", "502 941 479"],
        "prompt": f"""Tu es un extracteur de données de factures d'énergie. Voici le texte OCR d'une FACTURE DE GAZ de Gaz de Bordeaux.

PARTICULARITÉS GAZ DE BORDEAUX :
- NUMERO_FACTURE : après "FACTURE No" ou "No" en haut de page (8 chiffres, ex: "85026287", "85533469").
- DATE_FACTURE : après "du" dans "FACTURE No ... du JJ/MM/AAAA" (ex: "du 06/04/2023" → "06/04/2023"). Déjà au format JJ/MM/AAAA.
- MONTANT_HT : après "Total Hors T.V.A." sur la page récapitulative (page 1). Séparateur de milliers = espace, décimal = virgule → convertir en point (ex: "21 782,69 €" → "21782.69").
- TAUX_TVA : "20%".
- MONTANT_TTC : après "Net à Payer TTC" (ex: "26 027,21 €" → "26027.21"). Même règle de conversion.
- NOM_INSTALLATEUR : toujours "GAZ DE BORDEAUX".
- ADRESSE_TRAVAUX : chercher dans la section "LIEU DE CONSOMMATION" (page détail, verso). L'adresse du site de consommation apparaît après le nom du site (ex: "BLANCHISSERIE") — prendre la rue (ex: "AV DES ETATS DE BRETAGNE" ou "ALL SAINT MICHEL"). IGNORER le nom du site lui-même.
- COMMUNE_TRAVAUX : commune du lieu de consommation (ex: "TREGUIER").
- CODE_POSTAL : code postal du lieu de consommation (ex: "22220").
IGNORER ABSOLUMENT :
  * Adresse Gaz de Bordeaux : "6 place Ravezies", "33075 BORDEAUX CEDEX" — c'est le siège du fournisseur.
  * Adresse TSA : "TSA 30122", "41974 BLOIS CEDEX 9" — c'est l'adresse postale de paiement.
  * "BP 60" — boîte postale du client, pas l'adresse du site.
- SIRET : 50294147900011 / APE 3523Z

Extrais les champs suivants du texte OCR ci-dessous.
Si un champ n'est pas visible, mets null.
Réponds UNIQUEMENT en JSON valide, aucun texte avant ou après.
{JSON_TEMPLATE}

TEXTE OCR :
""",
    },
    "total_energies": {
        "detecter": ["totalenergies", "total energies", "privilege.collectivite@mail.totalenergies", "totalenergies.fr", "facture d'electricite"],
        "prompt": f"""Tu es un extracteur de données de factures d'énergie. Voici le texte OCR d'une FACTURE D'ELECTRICITE de TotalEnergies.

PARTICULARITÉS TOTALENERGIES :
- NUMERO_FACTURE : cherche "No" suivi d'un numéro long (9-12 chiffres, ex: "100005687322" ou "111003282441"). Souvent en haut de page après "FACTURE D'ELECTRICITE du ... No" et aussi en bas "Facture : No ...".
- DATE_FACTURE : date après "FACTURE D'ELECTRICITE du" (ex: "19 mai 2022" → "19/05/2022", "25 novembre 2022" → "25/11/2022"). Format JJ/MM/AAAA.
- MONTANT_HT : cherche "Total hors TVA" sur la page récapitulative (page 1). Format avec virgule (ex: "23773,37 €" → "23773.37").
- TAUX_TVA : taux principal appliqué à la consommation = "20%". Si TVA 5,5% aussi présente (sur l'abonnement), indiquer "20%" uniquement (taux dominant).
- MONTANT_TTC : cherche "Montant TTC" (ex: "28528,04 €" → "28528.04").
- NOM_INSTALLATEUR : toujours "TOTALENERGIES".
- ADRESSE_TRAVAUX : adresse du/des site(s) de consommation. Chercher dans les pages de détail, section "Adresse du site" ou dans la ligne "Code interne: ... ALLEE/RUE ... COMMUNE". Si plusieurs sites, concaténer séparés par " | ". IGNORER les adresses TotalEnergies (TSA 71632, 75901 PARIS CEDEX 15) et Enedis.
- COMMUNE_TRAVAUX : commune(s) du/des site(s). Si plusieurs sites avec la même commune, n'indiquer qu'une fois. Si communes différentes, séparer par " | ".
- CODE_POSTAL : code(s) postal(aux) du/des site(s). Si tous identiques, n'indiquer qu'une fois. Si différents, séparer par " | ".

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
- MONTANT_HT : prendre UNIQUEMENT le montant à côté de "Total H.T." ou "TOTAL HT". IGNORER "Sous-total", acomptes, cumuls.
- MONTANT_TTC : prendre UNIQUEMENT le montant à côté de "Total T.T.C." ou "TOTAL TTC". IGNORER sous-totaux TTC.
- Installateur : Ternel Couverture, 8 rue de l'industrie, 80300 ALBERT

Extrais les champs suivants du texte OCR ci-dessous.
Si un champ n'est pas visible, mets null.
Pour TAUX_TVA avec taux multiples, indique "20% / 5.5%".
Réponds UNIQUEMENT en JSON valide, aucun texte avant ou après.
{JSON_TEMPLATE}

TEXTE OCR :
""",
    },
    "otis": {
        "detecter": ["otis", "542 107 800", "542107800", "tour defense plaza", "bobigny cedex"],
        "prompt": f"""Tu es un extracteur de données de factures BTP. Voici le texte OCR d'une facture de OTIS (ascenseurs, escalators, portes automatiques, élévateurs — Puteaux).

PARTICULARITÉS OTIS :
- Numéro facture : après "N° pièce :" ou "N° piece :". Format "U4 23004673" (préfixe U4 + espace + 8 chiffres) ou "DOF 7185057" (préfixe DOF + espace + 7 chiffres). Inclure le préfixe U4 ou DOF dans le numéro.
- DATE_FACTURE : date en haut à droite après "Date :". Format JJ/MM/AAAA. IGNORER la date du tampon S.I.P.
- TVA : 20,00%
- Montants : cherche sur la page 1 :
  * MONTANT_HT = "Montant HT" suivi du montant en EUR
  * MONTANT_TTC = "Montant total TTC à payer" ou "Montant total TTC a payer" suivi du montant en EUR
  * Si page 2 contient "TOTAL HT TOUS TRAVAUX", utiliser ce montant pour MONTANT_HT
- ADRESSE_TRAVAUX : dans le bloc "Concerne" à gauche sous le client. Prendre les lignes d'adresse (rue, numéro). IGNORER le code contrat (ex: "45TJWGOU 60060611"). IGNORER l'adresse d'OTIS (Tour Défense Plaza, Puteaux, Bobigny).
- COMMUNE_TRAVAUX : ville du site d'intervention dans le bloc "Concerne" (ex: "AMIENS"). IGNORER "PUTEAUX", "BOBIGNY" (adresses OTIS).
- CODE_POSTAL : code postal 5 chiffres du site (ex: "80000"). IGNORER "92800", "93736" (codes postaux OTIS).
- NOM_INSTALLATEUR : toujours "OTIS".
- SIRET : 542 107 800 / NAF/APE 4329B

Extrais les champs suivants du texte OCR ci-dessous.
Si un champ n'est pas visible, mets null.
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
- MONTANT_HT : montant à côté de "TOTAL HT", "Net HT", "Montant HT". IGNORER "Sous-total HT", "Sous-total HT/cumul", "Sous-total HT déjà facturé". TOUJOURS prendre le TOTAL, jamais un sous-total.
- TAUX_TVA : pourcentage TVA (ex: "20%", "10%", "5.5%")
- MONTANT_TTC : montant à côté de "TOTAL TTC", "Net à payer". IGNORER les sous-totaux TTC. Le TTC doit être > HT.
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
