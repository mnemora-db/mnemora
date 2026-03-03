"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Rocket,
  BookOpen,
  Code2,
  Puzzle,
  CreditCard,
  ChevronDown,
  ArrowLeft,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useState } from "react";

interface NavItem {
  label: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  children?: { label: string; href: string }[];
}

const navItems: NavItem[] = [
  { label: "Overview", href: "/docs", icon: BookOpen },
  { label: "Quickstart", href: "/docs/quickstart", icon: Rocket },
  { label: "Concepts", href: "/docs/concepts", icon: BookOpen },
  { label: "API Reference", href: "/docs/api-reference", icon: Code2 },
  {
    label: "Integrations",
    href: "/docs/integrations",
    icon: Puzzle,
    children: [
      { label: "LangGraph", href: "/docs/integrations/langgraph" },
      { label: "LangChain", href: "/docs/integrations/langchain" },
      { label: "CrewAI", href: "/docs/integrations/crewai" },
    ],
  },
  { label: "Pricing", href: "/docs/pricing", icon: CreditCard },
];

export default function DocsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const [integrationsOpen, setIntegrationsOpen] = useState(
    pathname.startsWith("/docs/integrations")
  );

  function isActive(href: string): boolean {
    if (href === "/docs") return pathname === "/docs";
    return pathname === href || pathname.startsWith(href + "/");
  }

  return (
    <div className="flex min-h-screen bg-[#09090B]">
      {/* Sidebar */}
      <aside className="fixed left-0 top-0 h-screen w-60 flex flex-col border-r border-[#27272A] bg-[#111114] z-30">
        {/* Header */}
        <div className="flex items-center gap-2 px-5 py-5 border-b border-[#27272A]">
          <Link
            href="/"
            className="flex items-center gap-2 group"
          >
            <div
              className="w-6 h-6 rounded-sm flex items-center justify-center bg-[#18181B] border border-[#3F3F46]"
              aria-hidden="true"
            >
              <svg
                width="14"
                height="14"
                viewBox="0 0 14 14"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
              >
                <path
                  d="M2 11V3L7 8L12 3V11"
                  stroke="#2DD4BF"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </div>
            <span className="font-sans font-semibold text-[15px] text-[#FAFAFA] tracking-tight">
              mnemora
            </span>
            <span className="text-xs text-[#52525B] font-medium ml-1">
              docs
            </span>
          </Link>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto" aria-label="Documentation">
          {navItems.map((item) => {
            if (item.children) {
              const parentActive = pathname.startsWith("/docs/integrations");
              return (
                <div key={item.label}>
                  <button
                    onClick={() => setIntegrationsOpen(!integrationsOpen)}
                    className={cn(
                      "w-full flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors duration-150",
                      parentActive
                        ? "text-[#FAFAFA]"
                        : "text-[#A1A1AA] hover:text-[#FAFAFA] hover:bg-[#18181B]"
                    )}
                  >
                    <item.icon
                      className={cn(
                        "w-4 h-4 shrink-0",
                        parentActive ? "text-teal-400" : "text-[#71717A]"
                      )}
                      aria-hidden="true"
                    />
                    <span className="flex-1 text-left">{item.label}</span>
                    <ChevronDown
                      className={cn(
                        "w-3.5 h-3.5 text-[#52525B] transition-transform duration-150",
                        integrationsOpen && "rotate-180"
                      )}
                      aria-hidden="true"
                    />
                  </button>
                  {integrationsOpen && (
                    <div className="ml-7 mt-0.5 space-y-0.5">
                      {item.children.map((child) => {
                        const childActive = pathname === child.href;
                        return (
                          <Link
                            key={child.href}
                            href={child.href}
                            className={cn(
                              "block px-3 py-1.5 rounded-md text-sm transition-colors duration-150",
                              childActive
                                ? "bg-[rgba(45,212,191,0.08)] text-teal-400"
                                : "text-[#71717A] hover:text-[#FAFAFA] hover:bg-[#18181B]"
                            )}
                          >
                            {child.label}
                          </Link>
                        );
                      })}
                    </div>
                  )}
                </div>
              );
            }

            const active = isActive(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors duration-150",
                  active
                    ? "bg-[rgba(45,212,191,0.08)] text-teal-400"
                    : "text-[#A1A1AA] hover:text-[#FAFAFA] hover:bg-[#18181B]"
                )}
              >
                <item.icon
                  className={cn(
                    "w-4 h-4 shrink-0",
                    active ? "text-teal-400" : "text-[#71717A]"
                  )}
                  aria-hidden="true"
                />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>

        {/* Bottom */}
        <div className="border-t border-[#27272A] p-3">
          <Link
            href="/dashboard"
            className="flex items-center gap-3 px-3 py-2 rounded-md text-sm text-[#A1A1AA] hover:text-[#FAFAFA] hover:bg-[#18181B] transition-colors duration-150"
          >
            <ArrowLeft className="w-4 h-4 text-[#71717A]" aria-hidden="true" />
            <span>Dashboard</span>
          </Link>
        </div>
      </aside>

      {/* Content */}
      <div className="flex-1 ml-60">
        <main className="max-w-3xl mx-auto px-8 py-12">{children}</main>
      </div>
    </div>
  );
}
