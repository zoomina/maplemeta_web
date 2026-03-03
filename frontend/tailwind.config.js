/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'bg-primary': '#0F1117',
        'bg-card': '#1A1D2E',
        'bg-card-hover': '#1F2440',
        'border-card': '#2A2D3E',
        'border-light': '#383B52',
        'accent': '#FF8C00',
        'accent-hover': '#E67C00',
        'text-main': '#F1F5F9',
        'text-sub': '#94A3B8',
        'text-muted': '#64748B',
        'success': '#10B981',
        'danger': '#EF4444',
      },
    },
  },
  plugins: [],
}
