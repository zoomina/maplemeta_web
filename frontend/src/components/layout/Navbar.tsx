import { NavLink } from 'react-router-dom';

const NAV_ITEMS = [
  { path: '/', label: '홈' },
  { path: '/meta', label: '메타분석' },
  { path: '/jobs', label: '직업분석' },
  { path: '/patch-notes', label: '패치노트' },
];

export function Navbar() {
  return (
    <nav className="sticky top-0 z-40 bg-[#1A1D2E] border-b border-[#2A2D3E]">
      <div className="max-w-7xl mx-auto px-4 h-14 flex items-center justify-between">
        <NavLink to="/" className="text-xl font-black tracking-tight">
          <span className="text-[#FF8C00]">MAPLE</span>
          <span className="text-[#F1F5F9] ml-1">META</span>
        </NavLink>
        <div className="flex items-center gap-1">
          {NAV_ITEMS.map(({ path, label }) => (
            <NavLink
              key={path}
              to={path}
              end={path === '/'}
              className={({ isActive }) =>
                `px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                  isActive
                    ? 'text-[#FF8C00] bg-[#FF8C00]/10'
                    : 'text-[#94A3B8] hover:text-[#F1F5F9] hover:bg-[#2A2D3E]'
                }`
              }
            >
              {label}
            </NavLink>
          ))}
        </div>
      </div>
    </nav>
  );
}
