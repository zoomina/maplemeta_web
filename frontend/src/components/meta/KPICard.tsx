// KPICard: 반원형 게이지 KPI 카드
// balance: 0–100, 좌→우 채움 아크, 구간별 색상, 숫자는 아크 내부 중앙
// shift: 바늘(needle) 스피도미터 스타일, 가운데=0, 좌=음수, 우=양수, 컬러 세그먼트
// 변경일: 260313 (260313_update.md 항목 2)

const CX = 50;
const CY = 50;
const R = 36;
const SW = 9;
const SHIFT_MAX = 20;
const SEG_GAP = 0.013;

/** fraction 0=왼쪽끝, 0.5=상단, 1=오른쪽끝 → SVG 좌표 */
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
  const large = 0; // 반원은 항상 180° 미만이므로 large-arc 불필요
  return `M ${x1} ${y1} A ${R} ${R} 0 ${large} 0 ${x2} ${y2}`;
}

function balanceColor(s: number): string {
  if (s >= 80) return '#22C55E';
  if (s >= 65) return '#84CC16';
  if (s >= 50) return '#EAB308';
  if (s >= 35) return '#F97316';
  return '#EF4444';
}

// shift 게이지 세그먼트: 중앙=녹색, 외곽=빨강
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

  // ── Balance 계산 ────────────────────────────────────────
  const balFraction = isBalance && value != null
    ? Math.max(0, Math.min(100, value)) / 100
    : 0;
  const balColor = isBalance && value != null ? balanceColor(value) : '#383B52';
  const bgPath = arcPath(0, 1);
  const valPath = isBalance && value != null && balFraction > 0.005
    ? (balFraction >= 0.995 ? bgPath : arcPath(0, balFraction))
    : '';

  // ── Shift 계산 ─────────────────────────────────────────
  const needleFrac = !isBalance && value != null
    ? 0.5 + Math.max(-SHIFT_MAX, Math.min(SHIFT_MAX, value)) / (2 * SHIFT_MAX)
    : 0.5;
  const [ntX, ntY] = arcPoint(needleFrac);
  // 바늘 삼각형: 밑변은 중심점에서 바늘 방향의 수직으로 확장
  const nAngle = (1 - needleFrac) * Math.PI;
  const bw = 2.8;
  const blX = +(CX - bw * Math.sin(nAngle)).toFixed(2);
  const blY = +(CY - bw * Math.cos(nAngle)).toFixed(2);
  const brX = +(CX + bw * Math.sin(nAngle)).toFixed(2);
  const brY = +(CY + bw * Math.cos(nAngle)).toFixed(2);

  // ── 표시 숫자 ──────────────────────────────────────────
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
            /* ── Balance 게이지 ── */
            <svg viewBox="0 0 100 68" className="w-full">
              {/* 배경 반원 */}
              <path d={bgPath} fill="none" stroke="#2A2D3E" strokeWidth={SW} strokeLinecap="round" />
              {/* 값 반원 */}
              {valPath && (
                <path d={valPath} fill="none" stroke={balColor} strokeWidth={SW} strokeLinecap="round" />
              )}
              {/* 현재값 끝점 마커 */}
              {balFraction > 0.02 && balFraction < 0.98 && (
                <circle cx={arcPoint(balFraction)[0]} cy={arcPoint(balFraction)[1]} r={2} fill={balColor} />
              )}
              {/* 값 숫자 (아크 내부 중앙) */}
              <text x={CX} y={46} textAnchor="middle" fill={balColor} fontSize="20" fontWeight="900">
                {numStr}
              </text>
              <text x={CX} y={56} textAnchor="middle" fill="#64748B" fontSize="8">
                {unit}
              </text>
              {/* 0 / 100 라벨 */}
              <text x={13} y={62} textAnchor="middle" fill="#475569" fontSize="7">0</text>
              <text x={87} y={62} textAnchor="middle" fill="#475569" fontSize="7">100</text>
            </svg>
          ) : (
            /* ── Shift 바늘 게이지 ── */
            <svg viewBox="0 0 100 72" className="w-full">
              {/* 컬러 세그먼트 */}
              {SHIFT_SEGS.map(([f1, f2, color], i) => (
                <path key={i} d={arcPath(f1, f2)} fill="none" stroke={color} strokeWidth={SW} strokeLinecap="butt" />
              ))}
              {/* 바늘 삼각형 */}
              <polygon points={`${ntX},${ntY} ${blX},${blY} ${brX},${brY}`} fill="#CBD5E1" />
              {/* 피벗 */}
              <circle cx={CX} cy={CY} r={5} fill="#334155" />
              <circle cx={CX} cy={CY} r={2.5} fill="#CBD5E1" />
              {/* 값 숫자 */}
              <text x={CX} y={64} textAnchor="middle" fill="#E2E8F0" fontSize="15" fontWeight="900">
                {numStr}
              </text>
              <text x={CX} y={72} textAnchor="middle" fill="#64748B" fontSize="8">
                {unit}
              </text>
              {/* − / + 라벨 */}
              <text x={13} y={57} textAnchor="middle" fill="#EF4444" fontSize="10" fontWeight="700">−</text>
              <text x={87} y={57} textAnchor="middle" fill="#22C55E" fontSize="10" fontWeight="700">+</text>
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
