/** 波动分解瀑布图：从 0 逐级累加到总波动，最后一级是残差。 */
import { fmtSigned } from '../../utils/format';
import type { SwingFactor } from '../../types/models';

export default function WaterfallChart({
  factors,
  deltaTotal,
  residual,
  unit = '元',
}: {
  factors: SwingFactor[];
  deltaTotal: number;
  residual: number;
  unit?: string;
}) {
  if (!factors.length) return null;
  const rows = [
    ...factors.map((item) => ({
      label: item.path_label,
      hint: item.dim_label,
      delta: item.delta_value,
      kind: 'factor' as const,
    })),
    { label: '残差（未解释）', hint: '其余组合', delta: residual, kind: 'residual' as const },
  ];
  const rowHeight = 30;
  const width = 900;
  const labelWidth = 250;
  const padRight = 120;
  const top = 30;
  const height = top + rows.length * rowHeight + 46;

  let cursor = 0;
  const steps = rows.map((row) => {
    const from = cursor;
    const to = cursor + row.delta;
    cursor = to;
    return { ...row, from, to };
  });
  const extent = Math.max(Math.abs(deltaTotal), ...steps.map((step) => Math.max(Math.abs(step.from), Math.abs(step.to))), 1);
  const plotWidth = width - labelWidth - padRight;
  const zeroX = labelWidth + plotWidth * 0.5;
  const x = (value: number) => zeroX + (value / (extent * 1.12)) * (plotWidth * 0.5);

  return (
    <div className="scroll-x">
      <svg
        viewBox={`0 0 ${width} ${height}`}
        preserveAspectRatio="xMinYMin meet"
        style={{ width: '100%', height: 'auto', minWidth: 660, display: 'block' }}
        role="img"
        aria-label="波动分解瀑布图"
        data-testid="waterfall-chart"
      >
        <line x1={zeroX} y1={top - 8} x2={zeroX} y2={height - 30} stroke="oklch(0.712 0.02 242)" strokeWidth={1.4} />
        <line
          x1={x(deltaTotal)}
          y1={top - 8}
          x2={x(deltaTotal)}
          y2={height - 30}
          stroke="oklch(0.545 0.168 26)"
          strokeWidth={1.4}
          strokeDasharray="5 4"
        />
        <text x={x(deltaTotal)} y={height - 12} textAnchor="middle" fontSize={10} fill="oklch(0.545 0.168 26)">
          总波动 {fmtSigned(deltaTotal)} {unit}
        </text>

        {steps.map((step, index) => {
          const y = top + index * rowHeight;
          const left = Math.min(x(step.from), x(step.to));
          const barWidth = Math.max(2, Math.abs(x(step.to) - x(step.from)));
          const negative = step.delta < 0;
          const color =
            step.kind === 'residual'
              ? 'oklch(0.612 0.016 248)'
              : negative
                ? 'oklch(0.545 0.168 26)'
                : 'oklch(0.505 0.088 168)';
          return (
            <g key={`${step.label}-${index}`}>
              <text x={0} y={y + 15} fontSize={11.5} fill="oklch(0.275 0.028 252)" fontFamily="'Barlow Condensed', sans-serif">
                {step.label.length > 26 ? `${step.label.slice(0, 25)}…` : step.label}
              </text>
              <text x={0} y={y + 26} fontSize={9} fill="oklch(0.648 0.018 248)">
                {step.hint}
              </text>
              <rect x={left} y={y + 4} width={barWidth} height={16} rx={1.5} fill={color} fillOpacity={0.9} />
              {index > 0 ? (
                <line
                  x1={x(step.from)}
                  y1={y - 6}
                  x2={x(step.from)}
                  y2={y + 4}
                  stroke="oklch(0.808 0.014 242)"
                  strokeWidth={1}
                  strokeDasharray="2 2"
                />
              ) : null}
              <text
                x={negative ? left - 6 : left + barWidth + 6}
                y={y + 16}
                textAnchor={negative ? 'end' : 'start'}
                fontSize={10.5}
                fill={color}
                fontFamily="'Barlow Condensed', sans-serif"
              >
                {fmtSigned(step.delta)}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
