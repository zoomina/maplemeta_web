// KPICard: 반원형 게이지 KPI 카드
// balance: 우(0)에서 시작해 좌(100) 방향으로 채움
// shift: 바늘 스타일, 중앙=0, 우=음수, 좌=양수
// 변경일: 260313

const CX = 50;
const CY = 50;
const R = 36;
const SW = 9;
const SHIFT_MAX = 20;
const SEG_GAP = 0.013;

/** fraction=0 → 좌 끝(9시), fraction=0.5 → 상단(12시), fraction=1 → 우 끝(3시) */
function arcPoint(fraction: number): [number, number] {
  const rad = (1 - fraction) * Math.PI;
  return [
    +(CX + R * Math.cos(rad)).toFixed(3),
    +(CY - R * Math.sin(rad)).toFixed(3),
  ];
}

function arcPath(f1: number, f2: number): string {
  const [x1, y1] = arcPoint(f1);
  const [x2, y2] = arcPoint(f2);
  return `M ${x1} ${y1} A ${R} ${R} 0 0 0 ${x2} ${y2}`;
}

function balanceColor(s: number): string {
  if (s >= 80) return '#22C55E';
  if (s >= 65) return '#84CC16';
  if (s >= 50) return '#EAB308';
  if (s >= 35) return '#F97316';
  return '#EF4444';
}

// 세그먼트: fraction=0(좌)=양수 극단, fraction=0.5(상단)=0, fraction=1(우)=음수 극단
const SHIFT_SEGS: [number, number, string][] = [
  [SEG_GAP,           0.125 - SEG_GAP, '#EF4444'],
  [0.125 + SEG_GAP,   0.250 - SEG_GAP, '#F97316'],
  [0.250 + SEG_GAP,   0.375 - SEG_GAP, '#EAB308'],
  [0.375 + SEG_GAP,   0.500 - SEG_GAP, '#86EFAC'],
  [0.500 + SEG_GAP,   0.625 - SEG_GAP, '#86EFAC'],
  [0.625 + SEG_GAP,   0.750 - SEG_GAP, '#EAB308'],
  [0.750 + SEG_GAP,   0.875 - SEG_GAP, '#F97316'],
  [0.875 + SEG_GAP,   1.000 - SEG_GAP, '#EF4444'],
];

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

  // ── Balance ──────────────────────────────────────────
  const balFraction = isBalance && value != null
    ? Math.max(0, Math.min(100, value)) / 100
    : 0;
  const balColor = isBalance && value != null ? balanceColor(value) : '#383B52';
  const bgPath = arcPath(0, 1);

  // 채움: 우측 끝(fraction=1)에서 시작해 balFraction만큼 좌로
  // arcPath(1 - balFraction, 1) → 우측 끝까지의 호
  const fillStart = 1 - balFraction;
  const valPath = isBalance && value != null && balFraction > 0.005
    ? (balFraction >= 0.995 ? bgPath : arcPath(fillStart, 1))
    : '';

  // ── Shift ────────────────────────────────────────────
  // value=0 → 0.5(상단), value<0(음수) → 0.5 이상(우쪽), value>0(양수) → 0.5 미만(좌쪽)
  const needleFrac = !isBalance && value != null
    ? 0.5 - Math.max(-SHIFT_MAX, Math.min(SHIFT_MAX, value)) / (2 * SHIFT_MAX)
    : 0.5;
  const [ntX, ntY] = arcPoint(needleFrac);
  const nAngle = (1 - needleFrac) * Math.PI;
  const bw = 2.8;
  const blX = +(CX - bw * Math.sin(nAngle)).toFixed(2);
  const blY = +(CY - bw * Math.cos(nAngle)).toFixed(2);
  const brX = +(CX + bw * Math.sin(nAngle)).toFixed(2);
  const brY = +(CY + bw * Math.cos(nAngle)).toFixed(2);

  // ── 숫자 ─────────────────────────────────────────────
  const numStr = value == null
    ? null
    : isBalance
      ? Math.round(value).toString()
      : (value >= 0 ? '+' : '') + value.toFixed(1);

  return (
    <div className="card flex flex-col items-center gap-2 py-4">
      <div className="text-xs font-semibold text-[#94A3B8] uppercase tracking-wider text-center leading-tight">
        {title}
      </div>

      {value == null ? (
        <div className="text-2xl font-bold text-[#383B52] py-6">준비중</div>
      ) : (
        <div className="relative w-full" style={{ maxWidth: 160 }}>
          {isBalance ? (
            <svg viewBox="0 0 100 68" className="w-full">
              {/* 배경 반원 */}
              <path d={bgPath} fill="none" stroke="#2A2D3E" strokeWidth={SW} strokeLinecap="round" />
              {/* 값 채움: 우→좌 방향 */}
              {valPath && (
                <path d={valPath} fill="none" stroke={balColor} strokeWidth={SW} strokeLinecap="round" />
              )}
              {/* 채움 경계 마커 */}
              {balFraction > 0.02 && balFraction < 0.98 && (
                <circle cx={arcPoint(fillStart)[0]} cy={arcPoint(fillStart)[1]} r={2} fill={balColor} />
              )}
              <text x={CX} y={46} textAnchor="middle" fill={balColor} fontSize="20" fontWeight="900">
                {numStr}
              </text>
              <text x={CX} y={56} textAnchor="middle" fill="#64748B" fontSize="8">
                {unit}
              </text>
              {/* 100=좌(fraction=0), 0=우(fraction=1) */}
              <text x={13} y={62} textAnchor="middle" fill="#475569" fontSize="7">100</text>
              <text x={87} y={62} textAnchor="middle" fill="#475569" fontSize="7">0</text>
            </svg>
          ) : (
            <svg viewBox="0 0 100 72" className="w-full">
              {/* 컬러 세그먼트 */}
              {SHIFT_SEGS.map(([f1, f2, color], i) => (
                <path key={i} d={arcPath(f1, f2)} fill="none" stroke={color} strokeWidth={SW} strokeLinecap="butt" />
              ))}
              {/* 바늘 */}
              <polygon points={`${ntX},${ntY} ${blX},${blY} ${brX},${brY}`} fill="#CBD5E1" />
              <circle cx={CX} cy={CY} r={5} fill="#334155" />
              <circle cx={CX} cy={CY} r={2.5} fill="#CBD5E1" />
              <text x={CX} y={64} textAnchor="middle" fill="#E2E8F0" fontSize="15" fontWeight="900">
                {numStr}
              </text>
              <text x={CX} y={72} textAnchor="middle" fill="#64748B" fontSize="8">
                {unit}
              </text>
              {/* +는 좌(fraction=0 근처), −는 우(fraction=1 근처) */}
              <text x={13} y={57} textAnchor="middle" fill="#22C55E" fontSize="10" fontWeight="700">+</text>
              <text x={87} y={57} textAnchor="middle" fill="#EF4444" fontSize="10" fontWeight="700">−</text>
            </svg>
          )}
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
