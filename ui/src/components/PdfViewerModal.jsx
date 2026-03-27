import { useState, useEffect, useRef, useCallback } from "react";
import { createPortal } from "react-dom";
import * as pdfjsLib from "pdfjs-dist";

pdfjsLib.GlobalWorkerOptions.workerSrc = new URL(
  "pdfjs-dist/build/pdf.worker.mjs",
  import.meta.url
).toString();

export default function PdfViewerModal({ fileUrl, title, onClose }) {
  const canvasRef = useRef(null);
  const [pdfDoc, setPdfDoc] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [scale, setScale] = useState(1.3);
  const renderingRef = useRef(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(false);

    fetch(fileUrl)
      .then((res) => {
        if (!res.ok) throw new Error("PDF non disponible");
        return res.arrayBuffer();
      })
      .then((data) => pdfjsLib.getDocument({ data }).promise)
      .then((pdf) => {
        if (cancelled) return;
        setPdfDoc(pdf);
        setTotalPages(pdf.numPages);
        setCurrentPage(1);
        setLoading(false);
      })
      .catch(() => {
        if (!cancelled) {
          setError(true);
          setLoading(false);
        }
      });

    return () => { cancelled = true; };
  }, [fileUrl]);

  useEffect(() => {
    if (!pdfDoc || !canvasRef.current) return;
    if (renderingRef.current) return;
    renderingRef.current = true;

    pdfDoc.getPage(currentPage).then((page) => {
      const viewport = page.getViewport({ scale });
      const canvas = canvasRef.current;
      if (!canvas) { renderingRef.current = false; return; }
      const ctx = canvas.getContext("2d");
      canvas.width = viewport.width;
      canvas.height = viewport.height;

      page.render({ canvasContext: ctx, viewport }).promise.then(() => {
        renderingRef.current = false;
      }).catch(() => {
        renderingRef.current = false;
      });
    });
  }, [pdfDoc, currentPage, scale]);

  const handleKeyDown = useCallback((e) => {
    if (e.key === "Escape") onClose();
    if (e.key === "ArrowRight" || e.key === "ArrowDown") {
      setCurrentPage((p) => Math.min(p + 1, totalPages));
    }
    if (e.key === "ArrowLeft" || e.key === "ArrowUp") {
      setCurrentPage((p) => Math.max(p - 1, 1));
    }
  }, [onClose, totalPages]);

  useEffect(() => {
    document.addEventListener("keydown", handleKeyDown);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = "";
    };
  }, [handleKeyDown]);

  const ctrlBtn = {
    background: "rgba(255,255,255,0.08)", border: "1px solid #475569",
    color: "#e2e8f0", fontSize: 14, cursor: "pointer", width: 30, height: 28,
    display: "flex", alignItems: "center", justifyContent: "center",
    borderRadius: 6, transition: "all 0.15s",
  };

  return createPortal(
    <div
      style={{
        position: "fixed", top: 0, left: 0, right: 0, bottom: 0,
        background: "rgba(15, 23, 42, 0.65)", backdropFilter: "blur(4px)",
        display: "flex", alignItems: "center", justifyContent: "center",
        zIndex: 99999, animation: "pdf-viewer-overlay-in 0.25s ease",
      }}
      onClick={onClose}
    >
      <div
        style={{
          width: "92vw", maxWidth: 950, height: "90vh",
          background: "#1e293b", borderRadius: 14,
          boxShadow: "0 25px 60px rgba(0,0,0,0.4)",
          display: "flex", flexDirection: "column", overflow: "hidden",
          animation: "pdf-viewer-slide-up 0.3s cubic-bezier(0.16,1,0.3,1)",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div style={{
          display: "flex", alignItems: "center", justifyContent: "space-between",
          padding: "12px 20px", background: "#0f172a", flexShrink: 0,
        }}>
          <span style={{ fontSize: 15, fontWeight: 700, color: "#FFF", fontFamily: "'Inter', sans-serif", letterSpacing: 0.5 }}>
            {title || "PDF Viewer"}
          </span>

          {pdfDoc && (
            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <button onClick={() => setScale((s) => Math.max(s - 0.2, 0.5))} style={ctrlBtn}>-</button>
              <span style={{ fontSize: 12, color: "#94a3b8", minWidth: 45, textAlign: "center" }}>
                {Math.round(scale * 100)}%
              </span>
              <button onClick={() => setScale((s) => Math.min(s + 0.2, 3))} style={ctrlBtn}>+</button>

              <div style={{ width: 1, height: 20, background: "#334155", margin: "0 6px" }} />

              <button onClick={() => setCurrentPage((p) => Math.max(p - 1, 1))}
                disabled={currentPage <= 1} style={ctrlBtn}>&#9664;</button>
              <span style={{ fontSize: 12, color: "#94a3b8", minWidth: 60, textAlign: "center" }}>
                {currentPage} / {totalPages}
              </span>
              <button onClick={() => setCurrentPage((p) => Math.min(p + 1, totalPages))}
                disabled={currentPage >= totalPages} style={ctrlBtn}>&#9654;</button>
            </div>
          )}

          <button onClick={onClose}
            style={{
              background: "none", border: "none", color: "#FFF", fontSize: 24,
              cursor: "pointer", width: 32, height: 32, display: "flex",
              alignItems: "center", justifyContent: "center", borderRadius: "50%",
              lineHeight: 1, transition: "background 0.15s",
            }}
            onMouseEnter={(e) => e.currentTarget.style.background = "rgba(255,255,255,0.15)"}
            onMouseLeave={(e) => e.currentTarget.style.background = "none"}
          >
            &times;
          </button>
        </div>

        {/* Body */}
        <div style={{
          flex: 1, overflow: "auto", display: "flex", justifyContent: "center",
          alignItems: loading || error ? "center" : "flex-start",
          padding: 20, background: "#334155",
        }}>
          {loading && <p style={{ fontSize: 14, color: "#94a3b8" }}>Chargement du PDF...</p>}
          {error && (
            <div style={{ textAlign: "center" }}>
              <p style={{ fontSize: 14, color: "#ef4444", marginBottom: 12 }}>Impossible de charger le PDF</p>
            </div>
          )}
          {pdfDoc && (
            <canvas ref={canvasRef} style={{ borderRadius: 4, boxShadow: "0 4px 20px rgba(0,0,0,0.3)" }} />
          )}
        </div>
      </div>
    </div>,
    document.body
  );
}
