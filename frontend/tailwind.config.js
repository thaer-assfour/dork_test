/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#0b1020",
        panel: "#141a2e",
        edge: "#26304d",
        accent: "#5b8cff",
      },
    },
  },
  plugins: [],
};
