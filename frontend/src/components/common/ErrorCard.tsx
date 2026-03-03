interface Props { message: string; onRetry?: () => void; }

export function ErrorCard({ message, onRetry }: Props) {
  return (
    <div className="card flex flex-col items-center gap-3 py-8 text-center">
      <div className="text-3xl">⚠️</div>
      <p className="text-[#94A3B8] text-sm">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-2 px-4 py-2 rounded-lg bg-[#FF8C00] text-[#0F1117] text-sm font-semibold hover:bg-[#E67C00] transition-colors"
        >
          다시 시도
        </button>
      )}
    </div>
  );
}
