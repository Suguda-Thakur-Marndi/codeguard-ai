import "./globals.css";
import React from "react";
import { Header } from "../components/Header";

export const metadata = {
  title: "CodeGuard AI — Pull Request Review Platform",
  description: "Production foundation for agentic GitHub Pull Request reviews (Phase 1)",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-slate-950 text-slate-100 min-h-screen flex flex-col antialiased">
        <Header />
        <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {children}
        </main>
        <footer className="border-t border-slate-900 py-6 text-center text-xs text-slate-500 font-mono">
          CodeGuard AI &bull; Phase 1: Production Foundation Active &bull; No AI analysis in Phase 1
        </footer>
      </body>
    </html>
  );
}
