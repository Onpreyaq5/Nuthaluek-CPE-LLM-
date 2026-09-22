import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        // โทนสีหลักอิงสีประจำมหาวิทยาลัย (น้ำเงิน–ทอง)
        brand: {
          50: "#eef4ff", 100: "#d9e6ff", 200: "#bcd2ff", 300: "#8eb4ff",
          400: "#598cff", 500: "#3366f2", 600: "#1f45d8", 700: "#1a37ae",
          800: "#1b318a", 900: "#1c2f6e", 950: "#141e46",
        },
        gold: { 400: "#f2c14e", 500: "#e0a92e", 600: "#b8851f" },
      },
      fontFamily: { sans: ["var(--font-sans)", "system-ui", "sans-serif"] },
    },
  },
  plugins: [],
};
export default config;
