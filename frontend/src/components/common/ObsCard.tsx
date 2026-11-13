/** 观测读数卡：k/v 两行的观测站风格小卡片。 */
export default function ObsCard({
  label,
  value,
  hint,
  tone = 'default',
}: {
  label: string;
  value: React.ReactNode;
  hint?: string;
  tone?: 'default' | 'alert' | 'cold';
}) {
  return (
    <div className={`readout${tone === 'alert' ? ' alert' : tone === 'cold' ? ' cold' : ''}`}>
      <div className="k">{label}</div>
      <div className="v">{value}</div>
      {hint ? <div className="tiny muted" style={{ marginTop: 2 }}>{hint}</div> : null}
    </div>
  );
}
