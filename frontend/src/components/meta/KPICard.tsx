// KPICard: 반원형 게이지 KPI 카드
// balance: 좌(0)에서 시작해 우(100) 방향으로 채움
// shift: 아크 스타일, 중앙=0, 좌=음수, 우=양수, 바늘 없음
// 변경일: 260314

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

/** A rx ry x-rotation large-arc sweep x y. sweep=1 → 위쪽 반원(좌→우), sweep=0이면 아래쪽 반원으로 뒤집혀 보임 */
function arcPath(f1: number, f2: number): string {
  const [x1, y1] = arcPoint(f1);
  const [x2, y2] = arcPoint(f2);
  return `M ${x1} ${y1} A ${R} ${R} 0 0 1 ${x2} ${y2}`;
}

function balanceColor(s: number): string {
  if (s >= 80) return '#22C55E';
  if (s >= 65) return '#84CC16';
  if (s >= 50) return '#EAB308';
  if (s >= 35) return '#F97316';
  return '#EF4444';
}

/** 중앙(0)에서 멀어질수록 빨간색 */
function shiftColor(frac: number): string {
  const dist = Math.abs(frac - 0.5) * 2; // 0=중앙, 1=극단
  if (dist < 0.25) return '#86EFAC';
  if (dist < 0.50) return '#EAB308';
  if (dist < 0.75) return '#F97316';
  return '#EF4444';
}

// 세그먼트: fraction=0(좌)=음수 극단, fraction=0.5(상단)=0, fraction=1(우)=양수 극단
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

  // 채움: 좌측 끝(fraction=0, 점수=0)에서 balFraction까지 (좌→우)
  const valPath = isBalance && value != null && balFraction > 0.005
    ? (balFraction >= 0.995 ? bgPath : arcPath(0, balFraction))
    : '';

  // ── Shift ────────────────────────────────────────────
  // value<0 → 좌(fraction<0.5), value>0 → 우(fraction>0.5)
  const needleFrac = !isBalance && value != null
    ? 0.5 + Math.max(-SHIFT_MAX, Math.min(SHIFT_MAX, value)) / (2 * SHIFT_MAX)
    : 0.5;
  const activeColor = !isBalance && value != null ? shiftColor(needleFrac) : '#86EFAC';

  // 활성 아크: 중앙(0.5)에서 값 위치까지
  const activePath = !isBalance && value != null && Math.abs(value) > 0.05
    ? (needleFrac < 0.5
        ? arcPath(needleFrac, 0.5)
        : arcPath(0.5, needleFrac))
    : '';

  // ── 숫자 (원본 int, 소수 절삭) ─────────────────────────
  const numStr = value == null
    ? null
    : isBalance
      ? Math.round(value).toString()
      : (value >= 0 ? '+' : '') + Math.round(value);

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
              {/* 값 채움: 좌→우 방향 (0에서 값까지) */}
              {valPath && (
                <path d={valPath} fill="none" stroke={balColor} strokeWidth={SW} strokeLinecap="round" />
              )}
              <text x={CX} y={46} textAnchor="middle" fill={balColor} fontSize="20" fontWeight="900">
                {numStr}
              </text>
              <text x={CX} y={56} textAnchor="middle" fill="#64748B" fontSize="8">
                {unit}
              </text>
              {/* 0=좌(fraction=0), 100=우(fraction=1) */}
              <text x={13} y={62} textAnchor="middle" fill="#475569" fontSize="7">0</text>
              <text x={87} y={62} textAnchor="middle" fill="#475569" fontSize="7">100</text>
            </svg>
          ) : (
            <svg viewBox="0 0 100 68" className="w-full">
              {/* 배경 컬러 세그먼트 (흐리게) */}
              {SHIFT_SEGS.map(([f1, f2, color], i) => (
                <path key={i} d={arcPath(f1, f2)} fill="none" stroke={color} strokeWidth={SW} strokeLinecap="butt" opacity="0.35" />
              ))}
              {/* 활성 아크: 중앙에서 값 위치까지 */}
              {activePath && (
                <path d={activePath} fill="none" stroke={activeColor} strokeWidth={SW} strokeLinecap="round" />
              )}
              <text x={CX} y={46} textAnchor="middle" fill={activeColor} fontSize="20" fontWeight="900">
                {numStr}
              </text>
              <text x={CX} y={56} textAnchor="middle" fill="#64748B" fontSize="8">
                {unit}
              </text>
              {/* −/+, 1번 카드 0/100과 동일 위치·스타일 */}
              <text x={13} y={62} textAnchor="middle" fill="#475569" fontSize="7">−</text>
              <text x={87} y={62} textAnchor="middle" fill="#475569" fontSize="7">+</text>
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
