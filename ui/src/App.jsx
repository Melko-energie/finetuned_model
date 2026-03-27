import { useState } from "react";
import Navbar from "./components/Navbar";
import Toast from "./components/Toast";
import GemmaTexte from "./pages/GemmaTexte";
import GemmaSmart from "./pages/GemmaSmart";
import OcrExtract from "./pages/OcrExtract";
import BatchZip from "./pages/BatchZip";
import "./App.css";

function App() {
  const [activeTab, setActiveTab] = useState("gemma-texte");
  const [toast, setToast] = useState(null);

  const showToast = (message, type = "success") => {
    setToast({ message, type, key: Date.now() });
  };

  return (
    <div className="app">
      <Navbar activeTab={activeTab} onTabChange={setActiveTab} />
      <main className="main-content">
        {activeTab === "gemma-texte" && <GemmaTexte onToast={showToast} />}
        {activeTab === "gemma-smart" && <GemmaSmart onToast={showToast} />}
        {activeTab === "ocr-extract" && <OcrExtract onToast={showToast} />}
        {activeTab === "batch-zip" && <BatchZip onToast={showToast} />}
      </main>
      <footer className="footer">
        <p>Stage 2026 — <strong>MADANI Yassine</strong> &middot; Gemma2:9b &middot; Melko Energie</p>
      </footer>
      {toast && (
        <Toast
          key={toast.key}
          message={toast.message}
          type={toast.type}
          onClose={() => setToast(null)}
        />
      )}
    </div>
  );
}

export default App;
