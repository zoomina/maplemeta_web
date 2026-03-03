import { LoadingSpinner } from './LoadingSpinner';

interface Props { visible: boolean; }

export function ColdStartOverlay({ visible }: Props) {
  if (!visible) return null;
  return (
    <div className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-[#0F1117]/90 backdrop-blur-sm">
      <div className="flex flex-col items-center gap-6 text-center px-6">
        <div className="text-5xl font-black text-[#FF8C00] tracking-tight">MAPLE</div>
        <div className="text-xl font-semibold text-[#F1F5F9]">서버를 깨우는 중입니다</div>
        <p className="text-sm text-[#94A3B8] max-w-xs leading-relaxed">
          데이터를 로드하는 중입니다.
        </p>
        <LoadingSpinner size="lg" className="mt-2" />
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
