interface Props { title: string; data: Record<string, unknown>[]; }

export function ShiftRankTable({ title, data }: Props) {
  if (!data.length) return (
    <div className="card">
      <h4 className="text-sm font-semibold text-[#F1F5F9] mb-2">{title}</h4>
      <p className="text-[#64748B] text-xs">데이터 없음</p>
    </div>
  );

  const keys = Object.keys(data[0]);

  return (
    <div className="card overflow-hidden p-0">
      <div className="px-4 py-3 border-b border-[#2A2D3E]">
        <h4 className="text-sm font-semibold text-[#F1F5F9]">{title}</h4>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[#2A2D3E]">
              {keys.map((k) => (
                <th key={k} className="px-4 py-2 text-left text-xs font-semibold text-[#94A3B8] uppercase tracking-wider">
                  {k}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.map((row, i) => (
              <tr key={i} className="border-b border-[#2A2D3E]/50 hover:bg-[#1F2440] transition-colors">
                {keys.map((k) => (
                  <td key={k} className="px-4 py-2.5 text-[#94A3B8]">
                    {k === '순위' ? (
                      <span className="text-[#FF8C00] font-semibold">{String(row[k])}</span>
                    ) : (
                      String(row[k] ?? '-')
                    )}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
