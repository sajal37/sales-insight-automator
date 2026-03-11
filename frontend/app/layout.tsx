import type { Metadata } from "next";
import { Toaster } from "sonner";
import "./globals.css";

export const metadata: Metadata = {
  title: "Sales Insight Automator — Rabbitt AI",
  description:
    "Upload sales data and instantly receive AI-generated executive briefs delivered to your inbox.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-screen bg-[var(--background)] text-[var(--foreground)] antialiased">
        <Toaster richColors position="top-right" />
        {children}
      </body>
    </html>
  );
}
