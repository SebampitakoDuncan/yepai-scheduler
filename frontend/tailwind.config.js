/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['DM Sans', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
      colors: {
        mcdonalds: {
          red: '#DA291C',
          yellow: '#FFC72C',
          gold: '#FFB81C',
        },
      },
    },
  },
  plugins: [],
};
