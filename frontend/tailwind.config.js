/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: [
          "Pretendard",
          "Inter",
          "ui-sans-serif",
          "system-ui",
          "Apple SD Gothic Neo",
          "Noto Sans KR",
          "sans-serif"
        ],
      },
      boxShadow: {
        soft: "0 20px 60px rgba(15, 23, 42, 0.08)",
      },
    },
  },
  plugins: [],
}
