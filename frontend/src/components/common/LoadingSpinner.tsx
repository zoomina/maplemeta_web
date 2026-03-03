interface Props { size?: 'sm' | 'md' | 'lg'; className?: string; }

export function LoadingSpinner({ size = 'md', className = '' }: Props) {
  const sz = size === 'sm' ? 'w-5 h-5' : size === 'lg' ? 'w-12 h-12' : 'w-8 h-8';
  return (
    <div className={`flex justify-center items-center ${className}`}>
      <div className={`${sz} border-2 border-[#2A2D3E] border-t-[#FF8C00] rounded-full animate-spin`} />
    </div>
  );
}
