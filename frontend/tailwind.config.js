/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        saarthi: {
          teal: {
            DEFAULT: '#0d9488',
            light: '#14b8a6',
            dark: '#0f766e',
            bg: '#f0fdfa'
          },
          amber: {
            DEFAULT: '#d97706',
            light: '#f59e0b',
            dark: '#b45309',
            bg: '#fffbeb'
          }
        }
      }
    },
  },
  plugins: [],
}

