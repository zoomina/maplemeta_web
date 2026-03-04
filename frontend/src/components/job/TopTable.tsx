import React from 'react';
interface Props { title: string; data: Record<string, unknown>[]; }

const HIDDEN_COLS = new Set(['이전순위', '순위변동', '점유율변동(%p)']);

function getDeltaColor(delta: number | null | undefined): string | undefined {
  if (delta == null || isNaN(delta)) return undefined;
  if (delta > 0) return '#ef4444';
  if (delta < 0) return '#3b82f6';
  return undefined;
}

function renderCell(key: string, row: Record<string, unknown>): React.ReactNode {
  const val = row[key];

  if (key === '현재순위') {
    const curr = val;
    const delta = row['순위변동'];
    const d = delta != null && delta !== '-' ? Number(delta) : null;
    const color = getDeltaColor(d);
    const sign = d != null && d > 0 ? '+' : '';
    const deltaStr = d != null && !isNaN(d) ? `(${sign}${d})` : '';
    return (
      <span>
        <span className="text-[#FF8C00] font-semibold">{String(curr ?? '-')}</span>
        {deltaStr && (
          <span style={{ color: color ?? '#94A3B8', marginLeft: 2, fontSize: '0.85em' }}>{deltaStr}</span>
        )}
      </span>
    );
  }

  if (key === '현재점유율(%)') {
    const share = val;
    const delta = row['점유율변동(%p)'];
    const d = delta != null && delta !== '-' ? Number(delta) : null;
    const color = getDeltaColor(d);
    const sign = d != null && d > 0 ? '+' : '';
    const deltaStr = d != null && !isNaN(d) ? `(${sign}${d.toFixed(2)}%p)` : '';
    return (
      <span>
        <span>{share != null ? `${share}%` : '-'}</span>
        {deltaStr && (
          <span style={{ color: color ?? '#94A3B8', marginLeft: 2, fontSize: '0.85em' }}>{deltaStr}</span>
        )}
      </span>
    );
  }

  if (key === '순위' || key === 'Rank') {
    return <span className="text-[#FF8C00] font-semibold">{String(val ?? '-')}</span>;
  }

  return <>{String(val ?? '-')}</>;
}

export function TopTable({ title, data }: Props) {
  if (!data.length) return (
    <div className="card">
      <h4 className="text-sm font-semibold text-[#F1F5F9] mb-1">{title}</h4>
      <p className="text-[#64748B] text-sm">데이터 없음</p>
    </div>
  );
  const allKeys = Object.keys(data[0]);
  const keys = allKeys.filter((k) => !HIDDEN_COLS.has(k));

  return (
    <div className="card overflow-hidden p-0">
      {title && (
        <div className="px-3 py-2 border-b border-[#2A2D3E]">
          <h4 className="text-sm font-semibold text-[#F1F5F9]">{title}</h4>
        </div>
      )}
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-[#2A2D3E]">
            {keys.map((k) => (
              <th key={k} className="px-3 py-2 text-left text-xs text-[#64748B] font-medium">{k}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, i) => (
            <tr key={i} className="border-b border-[#2A2D3E]/40 hover:bg-[#1F2440]">
              {keys.map((k) => (
                <td key={k} className="px-3 py-2 text-[#94A3B8]">
                  {renderCell(k, row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
