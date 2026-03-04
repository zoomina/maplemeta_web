import { useState } from 'react';
import { LoadingSpinner } from './LoadingSpinner';

interface Props { visible: boolean; }

export function ColdStartOverlay({ visible }: Props) {
  const [imgError, setImgError] = useState(false);
  if (!visible) return null;
  return (
    <div className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-[#0F1117]/90 backdrop-blur-sm">
      <div className="flex flex-col items-center gap-6 text-center px-6">
        {!imgError ? (
          <img
            src="/loading.gif"
            alt="로딩"
            className="h-20 w-auto object-contain"
            onError={() => setImgError(true)}
          />
        ) : (
          <LoadingSpinner size="lg" />
        )}
        <div className="text-xl font-semibold text-[#F1F5F9]">데이터 로딩중입니다.</div>
        <div className="flex gap-1.5 mt-2">
          {[0,1,2].map(i => (
            <div
              key={i}
              className="w-2 h-2 rounded-full bg-[#FF8C00] animate-bounce"
              style={{ animationDelay: `${i * 0.15}s` }}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
