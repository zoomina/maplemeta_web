import { NoticeItem } from '../../types';

interface Props { title: string; items: NoticeItem[]; }

export function NoticeList({ title, items }: Props) {
  return (
    <div className="card h-full">
      <h3 className="text-base font-bold text-[#F1F5F9] mb-3">{title}</h3>
      {items.length === 0 ? (
        <p className="text-[#64748B] text-sm">데이터 없음</p>
      ) : (
        <ul className="space-y-2">
          {items.map((item, i) => (
            <li key={i} className="flex justify-between items-start gap-3 group">
              <a
                href={item.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-[#94A3B8] hover:text-[#FF8C00] transition-colors flex-1 leading-snug"
              >
                {item.title}
              </a>
              <span className="text-xs text-[#64748B] whitespace-nowrap flex-shrink-0 pt-0.5">
                {item.date}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
