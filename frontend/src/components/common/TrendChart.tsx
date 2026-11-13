/** 指标趋势：等压线底纹 + 左侧风玫瑰刻度 + 异常点标注（SVG 自绘）。 */
import { fmtInt, shortDate } from '../../utils/format';
import type { TrendPoint } from '../../types/models';

export default function TrendChart({
  series,
  anomalyDate,
  anomalyLabel,
  baselineDate,
  height = 250,
}: {
  series: TrendPoint[];
  anomalyDate?: string;
  anomalyLabel?: string;
  baselineDate?: string;
  height?: number;
}) {
  if (!series.length) return null;
  const width = 900;
  const padLeft = 76;
  const padRight = 22;
  const padTop = 22;
  const padBottom = 34;
  const values = series.map((point) => point.value);
  const maxValue = Math.max(...values);
  const minValue = Math.min(...values);
  const span = Math.max(1, maxValue - minValue);
  const top = maxValue + span * 0.12;
  const bottom = Math.max(0, minValue - span * 0.12);
  const x = (index: number) =>
    padLeft + (series.length === 1 ? 0 : (index / (series.length - 1)) * (width - padLeft - padRight));
  const y = (value: number) =>
    padTop + (1 - (value - bottom) / Math.max(1, top - bottom)) * (height - padTop - padBottom);

  const line = series.map((point, index) => `${index === 0 ? 'M' : 'L'} ${x(index)} ${y(point.value)}`).join(' ');
  const area = `${line} L ${x(series.length - 1)} ${height - padBottom} L ${x(0)} ${height - padBottom} Z`;
  const anomalyIndex = series.findIndex((point) => point.date === anomalyDate);
  const baselineIndex = series.findIndex((point) => point.date === baselineDate);
  const gridValues = [0, 0.25, 0.5, 0.75, 1].map((ratio) => bottom + (top - bottom) * ratio);

  return (
    <div className="scroll-x">
      <svg
        viewBox={`0 0 ${width} ${height}`}
        preserveAspectRatio="xMinYMin meet"
        style={{ width: '100%', height: 'auto', minWidth: 620, display: 'block' }}
        role="img"
        aria-label="指标趋势"
        data-testid="trend-chart"
      >
        {/* 等压线底纹 */}
        {[0.9, 0.72, 0.54, 0.36].map((scale, index) => (
          <ellipse
            key={index}
            cx={width * 0.82}
            cy={padTop + 6}
            rx={(width * 0.46) * scale}
            ry={(height * 0.62) * scale}
            fill="none"
            stroke="oklch(0.72 0.052 240 / 0.22)"
            strokeWidth={1}
          />
        ))}

        {/* 横向刻度 + 风玫瑰小刻度 */}
        {gridValues.map((value) => (
          <g key={value}>
            <line x1={padLeft} y1={y(value)} x2={width - padRight} y2={y(value)} stroke="oklch(0.878 0.014 242)" />
            <text
              x={padLeft - 20}
              y={y(value) + 4}
              textAnchor="end"
              fontSize={10}
              fill="oklch(0.648 0.018 248)"
              fontFamily="'Barlow Condensed', sans-serif"
            >
              {(value / 1000).toFixed(0)}k
            </text>
          </g>
        ))}
        {Array.from({ length: 30 }).map((_, index) => {
          const tickY = padTop + (index / 29) * (height - padTop - padBottom);
          const long = index % 5 === 0;
          return (
            <line
              key={`rose-${index}`}
              x1={padLeft - (long ? 13 : 7)}
              y1={tickY}
              x2={padLeft - 2}
              y2={tickY}
              stroke={long ? 'oklch(0.712 0.02 242)' : 'oklch(0.808 0.014 242)'}
              strokeWidth={long ? 1.4 : 1}
            />
          );
        })}

        <path d={area} fill="oklch(0.52 0.088 245 / 0.14)" />
        <path d={line} fill="none" stroke="oklch(0.395 0.072 250)" strokeWidth={2.2} strokeLinejoin="round" />

        {series.map((point, index) =>
          index % 3 === 0 || index === series.length - 1 ? (
            <text
              key={point.date}
              x={x(index)}
              y={height - padBottom + 16}
              textAnchor="middle"
              fontSize={9.5}
              fill="oklch(0.648 0.018 248)"
              fontFamily="'Barlow Condensed', sans-serif"
            >
              {shortDate(point.date)}
            </text>
          ) : null,
        )}

        {baselineIndex >= 0 ? (
          <g>
            <line
              x1={x(baselineIndex)}
              y1={padTop}
              x2={x(baselineIndex)}
              y2={height - padBottom}
              stroke="oklch(0.52 0.088 245)"
              strokeWidth={1.4}
              strokeDasharray="4 3"
            />
            <text x={x(baselineIndex) + 4} y={padTop + 11} fontSize={9.5} fill="oklch(0.395 0.072 250)">
              基线 {shortDate(series[baselineIndex].date)}
            </text>
          </g>
        ) : null}

        {anomalyIndex >= 0 ? (
          <g>
            <line
              x1={x(anomalyIndex)}
              y1={padTop}
              x2={x(anomalyIndex)}
              y2={height - padBottom}
              stroke="oklch(0.545 0.168 26)"
              strokeWidth={1.8}
              strokeDasharray="2 3"
            />
            <circle cx={x(anomalyIndex)} cy={y(series[anomalyIndex].value)} r={6} fill="oklch(0.545 0.168 26)" />
            <circle cx={x(anomalyIndex)} cy={y(series[anomalyIndex].value)} r={11} fill="none" stroke="oklch(0.545 0.168 26)" strokeOpacity={0.45} />
            <text
              x={x(anomalyIndex) - 8}
              y={y(series[anomalyIndex].value) - 14}
              textAnchor="end"
              fontSize={11}
              fill="oklch(0.545 0.168 26)"
              fontFamily="'Barlow Condensed', sans-serif"
            >
              {shortDate(series[anomalyIndex].date)} · {fmtInt(series[anomalyIndex].value)}
            </text>
            {anomalyLabel ? (
              <text
                x={x(anomalyIndex) - 8}
                y={y(series[anomalyIndex].value) - 3}
                textAnchor="end"
                fontSize={9.5}
                fill="oklch(0.545 0.168 26)"
              >
                {anomalyLabel}
              </text>
            ) : null}
          </g>
        ) : null}
      </svg>
    </div>
  );
}
