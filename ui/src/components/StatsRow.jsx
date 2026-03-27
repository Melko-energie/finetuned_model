export default function StatsRow({ stats }) {
  return (
    <div className="stats-row">
      {stats.map((stat, i) => (
        <div className="stat-box" key={i}>
          <div className="stat-num">{stat.value}</div>
          <div className="stat-label">{stat.label}</div>
        </div>
      ))}
    </div>
  );
}
