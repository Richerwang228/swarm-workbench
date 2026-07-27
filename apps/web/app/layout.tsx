import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Swarm Workbench — Observable multi-agent work",
  description: "A local-first workspace for observable, bounded multi-agent work.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh" className="h-full">
      <body className="h-full">{children}</body>
    </html>
  );
}
