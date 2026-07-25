import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  weight: ["400", "500", "600"],
});

const jetbrains = JetBrains_Mono({
  variable: "--font-mono",
  subsets: ["latin"],
  weight: ["400", "500"],
});

export const metadata: Metadata = {
  title: "Swarm Workbench — Agent 集群控制台",
  description: "一个可观察、可复现的本地多 Agent 协作工作台",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh" className={`${inter.variable} ${jetbrains.variable} h-full`}>
      <body className="h-full">{children}</body>
    </html>
  );
}
