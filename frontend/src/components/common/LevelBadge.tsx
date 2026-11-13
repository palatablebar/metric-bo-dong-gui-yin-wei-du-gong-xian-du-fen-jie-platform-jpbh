import { ANOMALY_CLASS, ANOMALY_LABELS, type AnomalyLevel } from '../../constants/enums';

export default function LevelBadge({ level, label }: { level: string; label?: string }) {
  const key = (level in ANOMALY_LABELS ? level : 'normal') as AnomalyLevel;
  return <span className={ANOMALY_CLASS[key]}>{label || ANOMALY_LABELS[key]}</span>;
}
