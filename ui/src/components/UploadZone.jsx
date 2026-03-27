import { useState, useRef } from "react";
import { Upload } from "lucide-react";

export default function UploadZone({ accept, title, subtitle, onFileSelect }) {
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef(null);

  const handleDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) onFileSelect(file);
  };

  const handleChange = (e) => {
    const file = e.target.files[0];
    if (file) onFileSelect(file);
  };

  return (
    <div
      className={`upload-zone ${dragging ? "dragging" : ""}`}
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      onClick={() => inputRef.current?.click()}
    >
      <div className="upload-zone-icon">
        <Upload size={32} />
      </div>
      <div className="upload-zone-title">{title || "Deposez votre fichier ici"}</div>
      <div className="upload-zone-subtitle">{subtitle || "ou cliquez pour parcourir"}</div>
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        onChange={handleChange}
      />
    </div>
  );
}
