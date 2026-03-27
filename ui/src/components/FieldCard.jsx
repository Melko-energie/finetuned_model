export default function FieldCard({ label, value }) {
  const isDetected = value !== null && value !== undefined && value !== "null";
  const displayValue = isDetected
    ? Array.isArray(value) ? value.join(" | ") : String(value)
    : "Non detecte";

  return (
    <div className={`field-card ${isDetected ? "detected" : "missing"}`}>
      <div className="field-label">{label}</div>
      <div className={`field-value ${isDetected ? "" : "missing"}`}>
        {displayValue}
      </div>
    </div>
  );
}
