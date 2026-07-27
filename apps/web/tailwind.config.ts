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
          bg:        "#F6F3EA",
          surface:   "#FFFCF6",
          panel:     "#EFE9DD",
          border:    "#D9D1C3",
          "border-hi":"#C3B9A9",
          text:      "#1E2925",
          dim:       "#66716A",
          muted:     "#E8E1D5",
          blue:      "#2D6D78",
          green:     "#23785F",
          amber:     "#B96A2E",
          red:       "#B84940",
          purple:    "#A15C2D",
          pink:      "#B65769",
          teal:      "#28796E",
        },
        role: {
          pm:       "#B85B45",
          designer: "#9B6683",
          frontend: "#356E9B",
          backend:  "#247D6E",
          tester:   "#A67320",
          ops:      "#92712B",
        },
      },
      fontFamily: {
        sans: ["var(--font-sans)", "sans-serif"],
        serif: ["var(--font-display)", "serif"],
        mono: ["var(--font-mono)", "monospace"],
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
        "draw-line": {
          from: { strokeDashoffset: "120" },
          to: { strokeDashoffset: "0" },
        },
        "rise": {
          from: { opacity: "0", transform: "translateY(12px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        "pulse-dot": "pulse-dot 1.6s ease-in-out infinite",
        "slide-in":  "slide-in 0.25s ease-out forwards",
        "card-in":   "card-in 0.35s cubic-bezier(0.16,1,0.3,1) forwards",
        "blink":     "blink 1s step-end infinite",
        "feed-in":   "feed-in 0.2s ease-out forwards",
        "draw-line": "draw-line 1.6s ease-out forwards",
        "rise": "rise 0.55s cubic-bezier(0.16, 1, 0.3, 1) forwards",
      },
    },
  },
  plugins: [],
};

export default config;
