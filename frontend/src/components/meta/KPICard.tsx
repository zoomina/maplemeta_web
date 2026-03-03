interface Props {
  title: string;
  value: number | null | undefined;
  caption?: string;
  subtitle?: string;
  unit?: string;
}

export function KPICard({ title, value, caption, subtitle, unit = '점' }: Props) {
  return (
    <div className="card flex flex-col gap-2">
      <div className="text-xs font-semibold text-[#94A3B8] uppercase tracking-wider">{title}</div>
      {value == null ? (
        <div className="text-2xl font-bold text-[#383B52]">준비중</div>
      ) : (
        <div className="text-3xl font-black text-[#FF8C00]">
          {value.toLocaleString()}<span className="text-lg ml-1 text-[#94A3B8]">{unit}</span>
        </div>
      )}
      {caption && <p className="text-xs text-[#64748B] leading-snug">{caption}</p>}
      {subtitle && <p className="text-xs text-[#94A3B8]">{subtitle}</p>}
    </div>
  );
}
