"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { api, authStorage } from "../lib/api";

export const Header: React.FC = () => {
  const pathname = usePathname();
  const [apiReady, setApiReady] = useState<boolean | null>(null);
  const [currentUser, setCurrentUser] = useState<{ id: string; login: string; email?: string; role: string; picture?: string } | null>(null);

  useEffect(() => {
    // Check for token in URL query parameter (e.g. from Google OAuth callback)
    if (typeof window !== "undefined") {
      const urlParams = new URLSearchParams(window.location.search);
      const token = urlParams.get("token");
      if (token) {
        authStorage.setToken(token);
        const cleanUrl = window.location.pathname;
        window.history.replaceState({}, document.title, cleanUrl);
      }
    }

    api
      .getReadiness()
      .then((res) => setApiReady(res.status === "ready"))
      .catch(() => setApiReady(false));

    api
      .getAuthMe()
      .then((res) => {
        if (res.authenticated && res.user) {
          setCurrentUser(res.user);
        }
      })
      .catch(() => setCurrentUser(null));
  }, []);

  const handleLogout = async () => {
    try {
      await api.logout();
    } catch {
      authStorage.removeToken();
    }
    setCurrentUser(null);
    window.location.reload();
  };

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
                <span className="text-[10px] text-slate-400 -mt-1 font-mono">Policy Governance</span>
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

          {/* Right side controls: User Auth & System status pill */}
          <div className="flex items-center space-x-3">
            {/* User Auth Status / Sign in with Google */}
            {currentUser && currentUser.email ? (
              <div className="flex items-center space-x-2">
                <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded-md bg-slate-900 border border-slate-800 text-xs text-slate-300">
                  {currentUser.picture ? (
                    <img
                      src={currentUser.picture}
                      alt={currentUser.login}
                      className="w-4 h-4 rounded-full"
                    />
                  ) : (
                    <span className="w-2 h-2 rounded-full bg-indigo-400" />
                  )}
                  <span className="font-medium max-w-[130px] truncate" title={currentUser.email}>
                    {currentUser.login || currentUser.email}
                  </span>
                </div>
                <button
                  type="button"
                  onClick={handleLogout}
                  className="text-xs text-slate-400 hover:text-slate-200 px-2 py-1 rounded hover:bg-slate-900 transition-colors"
                >
                  Sign Out
                </button>
              </div>
            ) : (
              <a
                href={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1"}/auth/google/login`}
                className="flex items-center space-x-1.5 px-2.5 py-1 rounded-md bg-slate-900 hover:bg-slate-850 text-slate-300 hover:text-white border border-slate-800 hover:border-slate-700 text-xs font-medium transition-colors"
                title="Sign in with your Google account"
              >
                <svg className="w-3.5 h-3.5" viewBox="0 0 24 24">
                  <path
                    fill="#4285F4"
                    d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                  />
                  <path
                    fill="#34A853"
                    d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                  />
                  <path
                    fill="#FBBC05"
                    d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
                  />
                  <path
                    fill="#EA4335"
                    d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
                  />
                </svg>
                <span>Sign in with Google</span>
              </a>
            )}

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
