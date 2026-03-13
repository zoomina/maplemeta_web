// KPICard: 반원형(semicircle) 게이지 차트 KPI 카드
// balance 타입: 0~100 범위, 구간별 색상 (초록→빨강)
// shift 타입: 부호 포함 -100~100 범위, 양수=초록/음수=빨강, 방향 화살표 표시
// 변경일: 260313 (260313_update.md 항목 2)

const CX = 50, CY = 50, R = 38, SW = 10;

function gaugePoint(fraction: number) {
  const angleDeg = 180 - fraction * 180;
  const rad = (angleDeg * Math.PI) / 180;
  return {
    x: +(CX + R * Math.cos(rad)).toFixed(2),
    y: +(CY - R * Math.sin(rad)).toFixed(2),
  };
}

function balanceColor(score: number): string {
  if (score >= 80) return '#22C55E';
  if (score >= 65) return '#84CC16';
  if (score >= 50) return '#EAB308';
  if (score >= 35) return '#F97316';
  return '#EF4444';
}

function shiftColor(val: number): string {
  if (Math.abs(val) <= 3) return '#94A3B8';
  return val > 0 ? '#22C55E' : '#EF4444';
}

interface Props {
  title: string;
  value: number | null | undefined;
  caption?: string;
  subtitle?: string;
  unit?: string;
  type?: 'balance' | 'shift';
}

export function KPICard({ title, value, caption, subtitle, unit = '점', type = 'balance' }: Props) {
  const isBalance = type === 'balance';
  const SHIFT_MAX = 20; // 실질적 shift 최대 표시 범위

  let fraction = 0;
  let color = '#383B52';
  let displayDir = '';

  if (value != null) {
    if (isBalance) {
      fraction = Math.max(0, Math.min(100, value)) / 100;
      color = balanceColor(value);
    } else {
      fraction = Math.min(1, Math.abs(value) / SHIFT_MAX);
      color = shiftColor(value);
      if (value > 3) displayDir = '▲';
      else if (value < -3) displayDir = '▼';
    }
  }

  const bgPath = `M ${CX - R} ${CY} A ${R} ${R} 0 0 0 ${CX + R} ${CY}`;

  let valuePath = '';
  if (value != null && fraction > 0.01) {
    if (fraction >= 0.999) {
      valuePath = bgPath;
    } else {
      const pt = gaugePoint(fraction);
      const largeArc = fraction > 0.5 ? 1 : 0;
      valuePath = `M ${CX - R} ${CY} A ${R} ${R} 0 ${largeArc} 0 ${pt.x} ${pt.y}`;
    }
  }

  const numStr =
    value == null
      ? null
      : isBalance
        ? Math.round(value).toString()
        : (value >= 0 ? '+' : '') + Math.round(value).toString();

  return (
    <div className="card flex flex-col items-center gap-2 py-4">
      <div className="text-xs font-semibold text-[#94A3B8] uppercase tracking-wider text-center leading-tight">
        {title}
      </div>

      {value == null ? (
        <div className="text-2xl font-bold text-[#383B52] py-6">준비중</div>
      ) : (
        <div className="relative w-full" style={{ maxWidth: 148 }}>
          <svg viewBox="0 0 100 64" className="w-full overflow-visible">
            {/* 배경 반원 */}
            <path
              d={bgPath}
              fill="none"
              stroke="#2A2D3E"
              strokeWidth={SW}
              strokeLinecap="round"
            />
            {/* 값 반원 */}
            {valuePath && (
              <path
                d={valuePath}
                fill="none"
                stroke={color}
                strokeWidth={SW}
                strokeLinecap="round"
              />
            )}
            {/* 방향 표시 (shift 전용) */}
            {displayDir && (
              <text
                x={CX}
                y={CY + 6}
                textAnchor="middle"
                fill={color}
                fontSize="11"
                fontWeight="900"
              >
                {displayDir}
              </text>
            )}
            {/* 값 숫자 */}
            <text
              x={CX}
              y={displayDir ? CY + 17 : CY + 12}
              textAnchor="middle"
              fill={value == null ? '#383B52' : color}
              fontSize="14"
              fontWeight="900"
            >
              {numStr}
            </text>
            {/* 단위 */}
            <text
              x={CX}
              y={CY + 24}
              textAnchor="middle"
              fill="#64748B"
              fontSize="8"
            >
              {unit}
            </text>
          </svg>
        </div>
      )}

      {caption && (
        <p className="text-xs text-[#64748B] leading-snug text-center px-2">{caption}</p>
      )}
      {subtitle && (
        <p className="text-xs text-[#94A3B8] text-center px-2">{subtitle}</p>
      )}
    </div>
  );
}
