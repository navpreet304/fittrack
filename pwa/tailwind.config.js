/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#0D1B2A",
        accent: "#1A8FE3",
        success: "#1DBF73",
        danger: "#E8473F",
      },
    },
  },
  plugins: [],
};
