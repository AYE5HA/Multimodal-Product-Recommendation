function clamp(n) {
  const v = Number(n);
  if (Number.isNaN(v)) return 0;
  return Math.max(0, Math.min(1, v));
}

export default function ScoreBar({ label, value }) {
  const score = clamp(value);
  const pct = Math.round(score * 100);

  return (
    <div className="score-bar">
      <div className="score-bar__meta">
        <span className="score-bar__label">{label}</span>
        <span className="score-bar__value">{pct}%</span>
      </div>
      <div className="score-bar__track" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100} aria-label={label}>
        <div className="score-bar__fill" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}
