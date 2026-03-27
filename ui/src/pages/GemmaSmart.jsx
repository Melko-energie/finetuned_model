import { useState, useEffect } from "react";
import { Target } from "lucide-react";
import UploadZone from "../components/UploadZone";
import FieldCard from "../components/FieldCard";
import StatsRow from "../components/StatsRow";
import { extractSmart, getInstallateurs, exportExcel } from "../api/client";

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

export default function GemmaSmart({ onToast }) {
  const [installateurs, setInstallateurs] = useState([]);
  const [fournisseur, setFournisseur] = useState("Auto-detect");
  const [loading, setLoading] = useState(false);
  const [fields, setFields] = useState(null);
  const [detectedInst, setDetectedInst] = useState(null);
  const [error, setError] = useState(null);
  const [fileName, setFileName] = useState("");
  const [previewUrl, setPreviewUrl] = useState(null);
  const [showJson, setShowJson] = useState(false);

  useEffect(() => {
    getInstallateurs()
      .then((data) => setInstallateurs(data.installateurs || []))
      .catch(() => {});
  }, []);

  const handleFile = async (file) => {
    setFields(null);
    setError(null);
    setFileName(file.name);
    setPreviewUrl(URL.createObjectURL(file));
    setLoading(true);

    try {
      const data = await extractSmart(file, fournisseur);
      if (data.error) {
        setError(data.error);
      } else {
        setFields(data.fields);
        setDetectedInst(data.installateur);
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
        results: [{ filename: fileName, fields, installateur: detectedInst || "" }],
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${fileName.replace(/\.[^.]+$/, "")}_extraction_smart.xlsx`;
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
      <span className="badge badge-orange">
        <Target size={14} /> Gemma2:9b — Prompts specialises par fournisseur
      </span>

      <div className="info-box" style={{ marginTop: 12 }}>
        <strong>Gemma2 Smart</strong> detecte automatiquement le fournisseur a partir du texte OCR
        et utilise un <strong>prompt specialise</strong> adapte a ses factures
        (format n&#xB0; facture, taux TVA habituel, emplacement des montants).
        17 fournisseurs connus + prompt generique pour les inconnus.
        <strong> Necessite</strong> que l'OCR ait ete extrait via script 01.
      </div>

      <div className="form-group">
        <label>Choisir le fournisseur</label>
        <select
          className="form-select"
          value={fournisseur}
          onChange={(e) => setFournisseur(e.target.value)}
        >
          <option value="Auto-detect">Auto-detect</option>
          {installateurs.map((inst) => (
            <option key={inst} value={inst.toUpperCase()}>
              {inst.toUpperCase()}
            </option>
          ))}
          <option value="DEFAULT (generique)">DEFAULT (generique)</option>
        </select>
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
          Gemma2 Smart — detection fournisseur et extraction...
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
                {detectedInst && detectedInst !== "DEFAULT" ? (
                  <div className="fournisseur-box">
                    <Target size={14} style={{ display: "inline", verticalAlign: "middle", marginRight: 6 }} />
                    Fournisseur {fournisseur === "Auto-detect" ? "detecte automatiquement" : "choisi manuellement"} : <strong>{detectedInst.toUpperCase()}</strong> — prompt specialise utilise
                  </div>
                ) : (
                  <div className="fournisseur-box-default">
                    Fournisseur non reconnu — prompt generique utilise
                  </div>
                )}

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
                  { value: detectedInst ? detectedInst.toUpperCase() : "?", label: "Fournisseur" },
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
