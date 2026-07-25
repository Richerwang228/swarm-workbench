import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        gh: {
          bg:        "#0D1117",
          surface:   "#161B22",
          panel:     "#1C2128",
          border:    "#30363D",
          "border-hi":"#484F58",
          text:      "#C9D1D9",
          dim:       "#7D8590",
          muted:     "#21262D",
          blue:      "#58A6FF",
          green:     "#3FB950",
          amber:     "#D29922",
          red:       "#F85149",
          purple:    "#BC8CFF",
          pink:      "#F778BA",
          teal:      "#2DD4BF",
        },
        role: {
          pm:       "#A78BFA",
          designer: "#F472B6",
          frontend: "#60A5FA",
          backend:  "#2DD4BF",
          tester:   "#FBBF24",
          ops:      "#FB923C",
        },
      },
      fontFamily: {
        sans: ["var(--font-inter)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
      keyframes: {
        "pulse-dot": {
          "0%, 100%": { opacity: "1" },
          "50%":       { opacity: "0.25" },
        },
        "slide-in": {
          from: { opacity: "0", transform: "translateY(6px)" },
          to:   { opacity: "1", transform: "translateY(0)" },
        },
        "card-in": {
          from: { opacity: "0", transform: "scale(0.97) translateY(8px)" },
          to:   { opacity: "1", transform: "scale(1) translateY(0)" },
        },
        "blink": {
          "0%, 100%": { opacity: "1" },
          "50%":       { opacity: "0" },
        },
        "feed-in": {
          from: { opacity: "0", transform: "translateX(-8px)" },
          to:   { opacity: "1", transform: "translateX(0)" },
        },
      },
      animation: {
        "pulse-dot": "pulse-dot 1.6s ease-in-out infinite",
        "slide-in":  "slide-in 0.25s ease-out forwards",
        "card-in":   "card-in 0.35s cubic-bezier(0.16,1,0.3,1) forwards",
        "blink":     "blink 1s step-end infinite",
        "feed-in":   "feed-in 0.2s ease-out forwards",
      },
    },
  },
  plugins: [],
};

export default config;
