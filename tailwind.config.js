/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        ivory: '#F7F6EE',
        sage: '#EEF1E7',
        forest: '#123C2D',
        leaf: { DEFAULT: '#176B3A', dark: '#0D4F2B', accent: '#72B84A' },
      },
      fontFamily: { sans: ['Inter Variable', 'Inter', 'sans-serif'] },
    },
  },
  plugins: [],
};
