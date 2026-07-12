/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx}",
    "./components/**/*.{js,ts,jsx,tsx}",
    "./lib/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Palette storica (mantenuta per retro-compatibilità con l'area riservata)
        millennio: {
          blue: "#1D4ED8",
          green: "#16A34A",
          orange: "#EA580C",
          gray: "#6B7280",
        },
        // Brand (rosso) — ancorato al rosso del logo ufficiale (#E30613 = 600)
        brand: {
          50: "#fff1f2",
          100: "#ffe0e2",
          200: "#ffc7cb",
          300: "#ff9aa2",
          400: "#fb6470",
          500: "#ef3b49",
          600: "#e30613",
          700: "#bd0410",
          800: "#9b0a14",
          900: "#810f17",
        },
        // Accent (arancio energia) — ancorato a millennio.orange (#EA580C = 600)
        accent: {
          50: "#fff7ed",
          100: "#ffedd5",
          200: "#fed7aa",
          300: "#fdba74",
          400: "#fb923c",
          500: "#f97316",
          600: "#ea580c",
          700: "#c2410c",
          800: "#9a3412",
          900: "#7c2d12",
        },
      },
      fontFamily: {
        sans: ["var(--font-inter)", "system-ui", "-apple-system", "sans-serif"],
        display: ["var(--font-poppins)", "var(--font-inter)", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
