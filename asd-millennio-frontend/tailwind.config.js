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
        millennio: {
          blue: "#1D4ED8",
          green: "#16A34A",
          orange: "#EA580C",
          gray: "#6B7280",
        },
      },
    },
  },
  plugins: [],
};
