import { useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { useApiStatus } from "@/hooks/useApiStatus";

const NAV_ITEMS = [
  { to: "/", label: "Overview", end: true },
  { to: "/setup", label: "Set up review" },
  { to: "/review", label: "Review workspace" },
  { to: "/cvs", label: "All CVs" },
];

function ApiStatusDot({ status }: { status: "checking" | "online" | "offline" }) {
  const config = {
    checking: {
      dot: "bg-amber-400 animate-pulse",
      text: "Checking API…",
      badge: "border-amber-400/50 bg-amber-50/80 text-amber-800",
    },
    online: {
      dot: "bg-emerald-500 shadow-[0_0_8px_#34d399]",
      text: "API connected",
      badge: "border-[#BCD9B4] bg-[#BCD9B4]/30 text-emerald-950",
    },
    offline: {
      dot: "bg-rose-500 shadow-[0_0_8px_#f43f5e]",
      text: "API unreachable",
      badge: "border-rose-300 bg-rose-50 text-rose-800",
    },
  }[status];

  return (
    <div
      className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-medium backdrop-blur-md transition-all duration-300 ${config.badge}`}
    >
      <span className={`h-2 w-2 rounded-full ${config.dot}`} aria-hidden="true" />
      {config.text}
    </div>
  );
}

function NavLinkItem({ to, label, end }: { to: string; label: string; end?: boolean }) {
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) =>
        `relative rounded-lg px-3.5 py-2 text-sm font-medium transition-all duration-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#BCD9B4] ${
          isActive
            ? "bg-[#BCD9B4]/30 text-emerald-950 font-semibold border border-[#BCD9B4] shadow-sm"
            : "text-stone-600 hover:text-stone-900 hover:bg-stone-100/80"
        }`
      }
    >
      {({ isActive }) => (
        <>
          {label}
          {/* Active bottom indicator line */}
          {isActive && (
            <span className="absolute bottom-0 left-1/2 h-[2px] w-1/2 -translate-x-1/2 rounded-full bg-[#5A8052]" />
          )}
        </>
      )}
    </NavLink>
  );
}

export function AppLayout() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const apiStatus = useApiStatus();

  return (
    <div className="relative flex min-h-screen flex-col bg-[#FDFBF7] text-stone-800 selection:bg-[#BCD9B4] selection:text-stone-900">
      {/* Background Sage Ambient Glows for UX Depth */}
      <div className="pointer-events-none fixed top-0 left-1/4 h-96 w-96 -translate-y-1/2 rounded-full bg-[#BCD9B4]/20 blur-[120px]" />
      <div className="pointer-events-none fixed bottom-0 right-10 h-80 w-80 rounded-full bg-[#BCD9B4]/10 blur-[100px]" />

      {/* Header */}
      <header className="sticky top-0 z-30 border-b border-stone-200/80 bg-[#FDFBF7]/90 backdrop-blur-xl shadow-sm">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-3.5 sm:px-6">
          
          {/* Logo Design */}
          <NavLink to="/" className="group flex items-center gap-3 focus:outline-none">
            {/* LLM Sage Badge */}
            <span className="flex h-10 items-center justify-center rounded-lg bg-[#BCD9B4] px-3.5 font-sans text-xl font-extrabold tracking-wider text-emerald-950 shadow-sm transition-all duration-300 group-hover:bg-[#a8cd9f] group-hover:scale-105">
              LLM
            </span>

            {/* OPS Typography with Underline Accent */}
            <div className="relative flex items-center pl-0.5">
              <span className="font-sans text-lg font-black tracking-[0.2em] text-stone-900 transition-colors duration-300 group-hover:text-[#5A8052]">
                OPS
              </span>
              
              <span className="pointer-events-none absolute -bottom-1.5 left-0 h-[2.5px] w-full rounded-full bg-[#BCD9B4] transition-all duration-500 ease-in-out group-hover:w-[180px] md:group-hover:w-[40px]" />
            </div>
          </NavLink>

          {/* Desktop Navigation */}
          <nav className="hidden items-center gap-1.5 md:flex" aria-label="Primary">
            {NAV_ITEMS.map((item) => (
              <NavLinkItem key={item.to} {...item} />
            ))}
          </nav>

          {/* API Status */}
          <div className="hidden items-center gap-4 md:flex">
            <ApiStatusDot status={apiStatus} />
          </div>

          {/* Mobile Menu Toggle */}
          <button
            type="button"
            className="inline-flex items-center justify-center rounded-lg border border-stone-300 bg-white p-2 text-stone-700 hover:border-[#BCD9B4] hover:bg-stone-50 hover:text-stone-900 focus:outline-none focus:ring-2 focus:ring-[#BCD9B4] md:hidden"
            aria-expanded={mobileOpen}
            aria-controls="mobile-nav"
            aria-label="Toggle navigation menu"
            onClick={() => setMobileOpen((open) => !open)}
          >
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
              {mobileOpen ? (
                <path
                  d="M5 5l10 10M15 5 5 15"
                  stroke="currentColor"
                  strokeWidth="1.8"
                  strokeLinecap="round"
                />
              ) : (
                <path
                  d="M3 5h14M3 10h14M3 15h14"
                  stroke="currentColor"
                  strokeWidth="1.8"
                  strokeLinecap="round"
                />
              )}
            </svg>
          </button>
        </div>

        {/* Mobile Navigation Dropdown */}
        {mobileOpen && (
          <nav
            id="mobile-nav"
            className="flex flex-col gap-1.5 border-t border-stone-200 bg-[#FDFBF7]/95 px-4 py-4 backdrop-blur-2xl md:hidden"
            aria-label="Primary"
          >
            {NAV_ITEMS.map((item) => (
              <NavLinkItem key={item.to} {...item} />
            ))}
            <div className="mt-3 border-t border-stone-200 pt-3">
              <ApiStatusDot status={apiStatus} />
            </div>
          </nav>
        )}
      </header>

      {/* Main Page Area */}
      <main className="relative z-10 flex-1">
        <Outlet />
      </main>
    </div>
  );
}