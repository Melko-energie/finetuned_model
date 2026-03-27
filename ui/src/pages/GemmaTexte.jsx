import { useState } from "react";
import { FileText } from "lucide-react";
import UploadZone from "../components/UploadZone";
import FieldCard from "../components/FieldCard";
import StatsRow from "../components/StatsRow";
import { extractTexte, exportExcel } from "../api/client";

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

export default function GemmaTexte({ onToast }) {
  const [loading, setLoading] = useState(false);
  const [fields, setFields] = useState(null);
  const [error, setError] = useState(null);
  const [fileName, setFileName] = useState("");
  const [previewUrl, setPreviewUrl] = useState(null);
  const [showJson, setShowJson] = useState(false);

  const handleFile = async (file) => {
    setFields(null);
    setError(null);
    setFileName(file.name);
    setPreviewUrl(URL.createObjectURL(file));
    setLoading(true);

    try {
      const data = await extractTexte(file);
      if (data.error) {
        setError(data.error);
      } else {
        setFields(data.fields);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async () => {
    try {
      const blob = await exportExcel({
        results: [{ filename: fileName, fields, installateur: "gemma2-texte" }],
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${fileName.replace(/\.[^.]+$/, "")}_extraction.xlsx`;
      a.click();
      URL.revokeObjectURL(url);
      onToast?.("Excel exporte avec succes", "success");
    } catch {
      onToast?.("Erreur lors de l'export Excel", "error");
    }
  };

  const countDetected = () => {
    if (!fields) return 0;
    return [...FIELDS_LEFT, ...FIELDS_RIGHT].filter(
      (f) => fields[f.key] && fields[f.key] !== "null"
    ).length;
  };

  return (
    <div className="tab-page">
      <span className="badge badge-violet">
        <FileText size={14} /> Gemma2:9b — Extraction textuelle
      </span>

      <div className="warn-box" style={{ marginTop: 12 }}>
        <strong>Gemma2:9b</strong> utilise le texte OCR extrait par DocTR (script 01).
        Il ne voit pas l'image directement. Reconstruction des lignes par position Y
        pour preserver la structure des tableaux.
        <strong> Attention</strong> : necessite que l'OCR ait deja ete extrait via script 01.
      </div>

      <UploadZone
        accept=".png,.jpg,.jpeg,.pdf"
        title="Deposez votre facture ici"
        subtitle="Formats acceptes : PNG, JPG, PDF — OCR DocTR requis"
        onFileSelect={handleFile}
      />

      {loading && (
        <div className="loading">
          <div className="spinner" />
          Gemma2:9b analyse le texte OCR...
        </div>
      )}

      {(previewUrl || fields || error) && !loading && (
        <div className="preview-layout">
          <div className="preview-panel">
            <h3 className="section-title">Apercu du document</h3>
            {previewUrl && fileName.toLowerCase().endsWith(".pdf") ? (
              <iframe
                src={previewUrl}
                style={{ width: "100%", height: 500, borderRadius: 10, border: "1px solid var(--slate-200)" }}
                title="Preview"
              />
            ) : previewUrl ? (
              <img src={previewUrl} alt="Preview" />
            ) : null}
          </div>

          <div className="preview-panel">
            <h3 className="section-title">Champs extraits</h3>

            {error && <div className="error-box">{error}</div>}

            {fields && (
              <>
                <div className="fields-grid">
                  <div>
                    {FIELDS_LEFT.map((f) => (
                      <FieldCard key={f.key} label={f.label} value={fields[f.key]} />
                    ))}
                  </div>
                  <div>
                    {FIELDS_RIGHT.map((f) => (
                      <FieldCard key={f.key} label={f.label} value={fields[f.key]} />
                    ))}
                  </div>
                </div>

                <StatsRow stats={[
                  { value: `${countDetected()}/9`, label: "Champs detectes" },
                ]} />

                <div style={{ marginTop: 16, display: "flex", gap: 8 }}>
                  <button className="btn btn-success" onClick={handleExport}>
                    Exporter en Excel
                  </button>
                  <button className="json-toggle" onClick={() => setShowJson(!showJson)}>
                    {showJson ? "Masquer" : "JSON brut"}
                  </button>
                </div>

                {showJson && (
                  <pre className="json-content">
                    {JSON.stringify(fields, null, 2)}
                  </pre>
                )}
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
