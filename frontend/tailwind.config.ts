import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Off-white canvas & warm neutral grays
        canvas: "#FDFBF7",
        ink: {
          950: "#1A201B",
          900: "#222923",
          800: "#2E362F",
          700: "#3F4A40",
          600: "#556357",
          500: "#708072",
          400: "#8FA391",
          300: "#B3C4B5",
          200: "#D6E0D7",
          100: "#EDF2EE",
          50: "#F7FAF7",
        },
        // Sage & Forest Green Theme Accents
        signal: {
          DEFAULT: "#3A6B4C", // Replaced blue with a rich forest green
          dark: "#264833",
          light: "#E4EDE6",
        },
        approved: {
          DEFAULT: "#1F8A5B",
          bg: "#E7F5EE",
          border: "#BFE3D2",
        },
        review: {
          DEFAULT: "#B5750A",
          bg: "#FCF1DC",
          border: "#F3D89B",
        },
        rejected: {
          DEFAULT: "#C4372B",
          bg: "#FBEAE8",
          border: "#F1C3BD",
        },
      },
      fontFamily: {
        sans: [
          "Inter var",
          "Inter",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "sans-serif",
        ],
        display: ["Fraunces", "Georgia", "serif"],
      },
      boxShadow: {
        panel: "0 1px 2px rgba(26,32,27,0.06), 0 1px 1px rgba(26,32,27,0.04)",
      },
    },
  },
  plugins: [],
} satisfies Config;