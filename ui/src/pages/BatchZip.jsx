import { useState } from "react";
import { Package, ChevronDown, ChevronRight } from "lucide-react";
import UploadZone from "../components/UploadZone";
import FieldCard from "../components/FieldCard";
import StatsRow from "../components/StatsRow";
import { batchZip, exportExcelMulti } from "../api/client";

const FIELDS_LEFT = [
  { key: "NUMERO_FACTURE", label: "Numero de facture" },
  { key: "DATE_FACTURE", label: "Date de facture" },
  { key: "MONTANT_HT", label: "Montant HT" },
  { key: "TAUX_TVA", label: "Taux de TVA" },
  { key: "MONTANT_TTC", label: "Montant TTC" },
];

const FIELDS_RIGHT = [
  { key: "NOM_INSTALLATEUR", label: "Installateur" },
  { key: "COMMUNE_TRAVAUX", label: "Commune" },
  { key: "CODE_POSTAL", label: "Code Postal" },
  { key: "ADRESSE_TRAVAUX", label: "Adresse des travaux" },
];

export default function BatchZip({ onToast }) {
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState({ current: 0, total: 0, text: "" });
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);
  const [expandedItems, setExpandedItems] = useState({});
  const [zipName, setZipName] = useState("");

  const handleFile = async (file) => {
    setResults(null);
    setError(null);
    setZipName(file.name);
    setLoading(true);
    setProgress({ current: 0, total: 0, text: "Envoi du ZIP..." });

    try {
      const data = await batchZip(file);
      if (data.error) {
        setError(data.error);
      } else {
        setResults(data.results);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async () => {
    try {
      const blob = await exportExcelMulti({ results });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${zipName.replace(/\.[^.]+$/, "")}_batch_multi.xlsx`;
      a.click();
      URL.revokeObjectURL(url);
      onToast?.("Excel exporte avec succes", "success");
    } catch {
      onToast?.("Erreur lors de l'export Excel", "error");
    }
  };

  const toggleItem = (i) => {
    setExpandedItems((prev) => ({ ...prev, [i]: !prev[i] }));
  };

  const nbOk = results ? results.filter((r) => r.installateur !== "ERREUR").length : 0;
  const nbErr = results ? results.length - nbOk : 0;
  const installateurs = results
    ? [...new Set(results.filter((r) => r.installateur !== "ERREUR").map((r) => r.installateur))]
    : [];
  const nbMissing = results
    ? results
        .filter((r) => r.installateur !== "ERREUR")
        .reduce((acc, r) => {
          return acc + [...FIELDS_LEFT, ...FIELDS_RIGHT].filter(
            (f) => !r.fields[f.key] || r.fields[f.key] === "null"
          ).length;
        }, 0)
    : 0;

  return (
    <div className="tab-page">
      <span className="badge badge-orange">
        <Package size={14} /> Traitement par lot — ZIP multi-factures
      </span>

      <div className="info-box" style={{ marginTop: 12 }}>
        <strong>Mode batch</strong> : uploadez un ZIP contenant vos factures PDF.
        Le systeme cherche d'abord l'OCR pre-calcule (data/ocr_texts/),
        sinon fait l'OCR DocTR en memoire. Chaque facture est traitee avec le prompt
        specialise du fournisseur detecte. Export Excel multi-feuilles (une par installateur).
      </div>

      <UploadZone
        accept=".zip"
        title="Deposez votre dossier ZIP ici"
        subtitle="Le ZIP peut contenir des PDFs a la racine et/ou dans des sous-dossiers"
        onFileSelect={handleFile}
      />

      {loading && (
        <>
          <div className="progress-container">
            <div className="progress-bar-wrap">
              <div className="progress-bar-fill" style={{ width: "50%" }} />
            </div>
            <div className="progress-text">{progress.text || "Traitement batch..."}</div>
          </div>
          <div className="loading">
            <div className="spinner" />
            Traitement batch en cours...
          </div>
        </>
      )}

      {error && <div className="error-box">{error}</div>}

      {results && (
        <>
          <StatsRow stats={[
            { value: `${nbOk}/${results.length}`, label: "Factures traitees" },
            { value: installateurs.length, label: "Installateurs" },
            { value: nbMissing, label: "Champs manquants" },
            { value: nbErr, label: "Erreurs" },
          ]} />

          <h3 className="section-title" style={{ marginTop: 24 }}>Resultats par facture</h3>

          {results.map((res, i) => {
            const isErr = res.installateur === "ERREUR";
            const expanded = expandedItems[i];

            return (
              <div className="batch-result-item" key={i}>
                <div className="batch-result-header" onClick={() => toggleItem(i)}>
                  <div>
                    <span className="icon">{isErr ? "\u274C" : "\u2705"}</span>
                    {res.filename} — {res.installateur.toUpperCase()}
                    {res.source && (
                      <span style={{ fontSize: 12, color: "var(--slate-400)", marginLeft: 8 }}>
                        ({res.source})
                      </span>
                    )}
                  </div>
                  {expanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                </div>
                {expanded && (
                  <div className="batch-result-body">
                    {isErr ? (
                      <div className="error-box">Extraction echouee{res.source ? ` : ${res.source}` : ""}</div>
                    ) : (
                      <div className="fields-grid">
                        <div>
                          {FIELDS_LEFT.map((f) => (
                            <FieldCard key={f.key} label={f.label} value={res.fields[f.key]} />
                          ))}
                        </div>
                        <div>
                          {FIELDS_RIGHT.map((f) => (
                            <FieldCard key={f.key} label={f.label} value={res.fields[f.key]} />
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}

          <div style={{ marginTop: 24 }}>
            <button className="btn btn-success btn-lg" onClick={handleExport}>
              Telecharger Excel — {results.length} factures ({installateurs.length} feuilles)
            </button>
          </div>
        </>
      )}
    </div>
  );
}
