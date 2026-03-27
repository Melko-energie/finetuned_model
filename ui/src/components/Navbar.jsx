export default function Navbar({ activeTab, onTabChange }) {
  const tabs = [
    { id: "gemma-texte", label: "GEMMA2 TEXTE" },
    { id: "gemma-smart", label: "GEMMA2 SMART" },
    { id: "ocr-extract", label: "OCR + EXTRACTION" },
    { id: "batch-zip", label: "TRAITEMENT LOT" },
  ];

  return (
    <nav className="navbar">
      <div className="navbar-inner">
        <div className="navbar-brand">
          <h1>Extraction Factures BTP</h1>
          <span>Melko Energie</span>
        </div>
        <div className="navbar-tabs">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              className={`navbar-tab ${activeTab === tab.id ? "active" : ""}`}
              onClick={() => onTabChange(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>
    </nav>
  );
}
