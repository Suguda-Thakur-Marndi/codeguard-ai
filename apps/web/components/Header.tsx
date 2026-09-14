"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { api } from "../lib/api";

export const Header: React.FC = () => {
  const pathname = usePathname();
  const [apiReady, setApiReady] = useState<boolean | null>(null);

  useEffect(() => {
    api
      .getReadiness()
      .then((res) => setApiReady(res.status === "ready"))
      .catch(() => setApiReady(false));
  }, []);

  const navLinks = [
    { href: "/dashboard", label: "Dashboard" },
    { href: "/repositories", label: "Repositories" },
    { href: "/pull-requests", label: "Pull Requests" },
    { href: "/approvals", label: "Approvals" },
    { href: "/audit", label: "Audit Log" },
    { href: "/policies", label: "Policies" },
    { href: "/debug", label: "Dev Debug" },
  ];

  return (
    <header className="border-b border-slate-800 bg-slate-950/80 backdrop-blur sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Brand identity constructed with pure UI */}
          <div className="flex items-center space-x-8">
            <Link href="/dashboard" className="flex items-center space-x-2.5 group">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-600 to-purple-700 flex items-center justify-center shadow-lg shadow-indigo-500/20 border border-indigo-400/30">
                <span className="font-mono font-bold text-white text-sm tracking-tighter">CG</span>
              </div>
              <div className="flex flex-col">
                <span className="font-bold text-base tracking-tight text-white group-hover:text-indigo-400 transition-colors">
                  CodeGuard <span className="text-indigo-400 font-mono text-sm">AI</span>
                </span>
                <span className="text-[10px] text-slate-400 -mt-1 font-mono">Phase 5 MCP Governance</span>
              </div>
            </Link>

            <nav className="hidden md:flex space-x-1">
              {navLinks.map((link) => {
                const isActive = pathname === link.href || pathname.startsWith(`${link.href}/`);
                return (
                  <Link
                    key={link.href}
                    href={link.href}
                    className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                      isActive
                        ? "bg-slate-800 text-white border border-slate-700"
                        : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
                    }`}
                  >
                    {link.label}
                  </Link>
                );
              })}
            </nav>
          </div>

          {/* System status pill */}
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2 px-3 py-1 rounded-full bg-slate-900 border border-slate-800 text-xs">
              <span
                className={`w-2 h-2 rounded-full ${
                  apiReady === true
                    ? "bg-emerald-400 animate-pulse"
                    : apiReady === false
                    ? "bg-rose-500"
                    : "bg-amber-400"
                }`}
              />
              <span className="text-slate-400 font-mono">
                API:{" "}
                <span
                  className={
                    apiReady === true
                      ? "text-emerald-400 font-medium"
                      : apiReady === false
                      ? "text-rose-400 font-medium"
                      : "text-amber-400 font-medium"
                  }
                >
                  {apiReady === true ? "Online" : apiReady === false ? "Degraded" : "Checking..."}
                </span>
              </span>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};
