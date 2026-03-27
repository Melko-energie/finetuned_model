export default function MetricCard({ value, label, variant = "primary" }) {
  return (
    <div className={`metric-card ${variant}`}>
      <div className="metric-value">{value}</div>
      <div className="metric-label">{label}</div>
    </div>
  );
}
