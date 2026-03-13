// EventCarousel: "바로가기" 텍스트 링크 제거, 카드 자체를 클릭 시 리다이렉트
// 변경일: 260313 (260313_update.md 항목 1)
import { useState } from 'react';
import { EventItem } from '../../types';

interface Props { title: string; items: EventItem[]; }

export function EventCarousel({ title, items }: Props) {
  const [start, setStart] = useState(0);
  const visible = items.slice(start, start + 3);

  return (
    <div>
      <h3 className="text-base font-bold text-[#F1F5F9] mb-3">{title}</h3>
      <div className="flex items-center gap-2">
        <button
          onClick={() => setStart(Math.max(0, start - 1))}
          disabled={start === 0}
          className="w-8 h-8 flex-shrink-0 flex items-center justify-center rounded-lg bg-[#1A1D2E] border border-[#2A2D3E] text-[#94A3B8] hover:text-[#F1F5F9] hover:border-[#383B52] disabled:opacity-30 transition-all"
        >‹</button>

        <div className="flex-1 grid grid-cols-3 gap-3 min-h-[160px]">
          {visible.map((item, i) => {
            const inner = (
              <>
                {item.thumbnail ? (
                  <img
                    src={item.thumbnail}
                    alt={item.title}
                    className="w-full aspect-video object-cover rounded-lg bg-[#0F1117]"
                    onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
                  />
                ) : (
                  <div className="w-full aspect-video bg-[#0F1117] rounded-lg flex items-center justify-center text-[#383B52] text-xs">
                    이미지 없음
                  </div>
                )}
                <p className="text-sm font-semibold text-[#F1F5F9] line-clamp-2 leading-snug">
                  {item.title}
                </p>
                <p className="text-xs text-[#64748B]">{item.period}</p>
                <div className="mt-auto">
                  {item.dday && item.dday !== '상시' ? (
                    <span className="badge badge-accent text-xs">{item.dday}</span>
                  ) : (
                    <span className="badge text-xs">{item.dday || '상시'}</span>
                  )}
                </div>
              </>
            );

            if (item.url) {
              return (
                <a
                  key={i}
                  href={item.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="card flex flex-col gap-2 p-3 cursor-pointer hover:border-[#FF8C00]/50 hover:bg-[#1F2440] transition-colors no-underline"
                >
                  {inner}
                </a>
              );
            }
            return (
              <div key={i} className="card flex flex-col gap-2 p-3">
                {inner}
              </div>
            );
          })}
          {visible.length < 3 && Array.from({ length: 3 - visible.length }).map((_, i) => (
            <div key={`empty-${i}`} className="card opacity-0" />
          ))}
        </div>

        <button
          onClick={() => setStart(Math.min(items.length - 3, start + 1))}
          disabled={start >= items.length - 3}
          className="w-8 h-8 flex-shrink-0 flex items-center justify-center rounded-lg bg-[#1A1D2E] border border-[#2A2D3E] text-[#94A3B8] hover:text-[#F1F5F9] hover:border-[#383B52] disabled:opacity-30 transition-all"
        >›</button>
      </div>
    </div>
  );
}
