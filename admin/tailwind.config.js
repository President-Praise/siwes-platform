/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        navy: { DEFAULT: "#1E3A5F", dark: "#15293f" },
        gold: { DEFAULT: "#C9A84C", dark: "#b08e3a" },
      },
      fontFamily: {
        head: ["Georgia", "Times New Roman", "serif"],
      },
    },
  },
  plugins: [],
};
