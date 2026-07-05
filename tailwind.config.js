/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./frontend/src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['-apple-system', 'BlinkMacSystemFont', 'avenir next', 'avenir', 'segoe ui', 'helvetica neue', 'Adwaita Sans', 'Cantarell', 'Ubuntu', 'roboto', 'noto', 'helvetica', 'arial', 'sans-serif'],
      },
      colors: {
        slate: {
          50: 'rgb(var(--slate-50) / <alpha-value>)',
          100: 'rgb(var(--slate-100) / <alpha-value>)',
          200: 'rgb(var(--slate-200) / <alpha-value>)',
          300: 'rgb(var(--slate-300) / <alpha-value>)',
          400: 'rgb(var(--slate-400) / <alpha-value>)',
          500: 'rgb(var(--slate-500) / <alpha-value>)',
          600: 'rgb(var(--slate-600) / <alpha-value>)',
          700: 'rgb(var(--slate-700) / <alpha-value>)',
          800: 'rgb(var(--slate-800) / <alpha-value>)',
          900: 'rgb(var(--slate-900) / <alpha-value>)',
          950: 'rgb(var(--slate-950) / <alpha-value>)',
        },
        cyan: {
          50: 'rgb(var(--cyan-50) / <alpha-value>)',
          100: 'rgb(var(--cyan-100) / <alpha-value>)',
          200: 'rgb(var(--cyan-200) / <alpha-value>)',
          300: 'rgb(var(--cyan-300) / <alpha-value>)',
          400: 'rgb(var(--cyan-400) / <alpha-value>)',
          500: 'rgb(var(--cyan-500) / <alpha-value>)',
          600: 'rgb(var(--cyan-600) / <alpha-value>)',
          700: 'rgb(var(--cyan-700) / <alpha-value>)',
          800: 'rgb(var(--cyan-800) / <alpha-value>)',
          900: 'rgb(var(--cyan-900) / <alpha-value>)',
          950: 'rgb(var(--cyan-950) / <alpha-value>)',
        }
      }
    },
  },
  plugins: [],
};
