"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Bot,
  BarChart2,
  KeyRound,
  BookOpen,
  Settings,
  User,
  MessageSquare,
} from "lucide-react";
import { useSession } from "next-auth/react";
import { cn } from "@/lib/utils";

interface NavItem {
  label: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
}

const navItems: NavItem[] = [
  { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { label: "Agents", href: "/dashboard/agents", icon: Bot },
  { label: "Usage", href: "/dashboard/usage", icon: BarChart2 },
  { label: "API Keys", href: "/dashboard/api-keys", icon: KeyRound },
  {
    label: "Docs",
    href: "/docs",
    icon: BookOpen,
  },
];

const ADMIN_GITHUB_USERNAME = "isaacgbc";

export function Sidebar() {
  const pathname = usePathname();
  const { data: session } = useSession();
  const isAdmin = session?.user?.name === ADMIN_GITHUB_USERNAME;

  function isActive(href: string): boolean {
    if (href === "/dashboard") {
      return pathname === "/dashboard";
    }
    return pathname.startsWith(href);
  }

  return (
    <aside
      className="fixed left-0 top-0 h-screen w-60 flex flex-col border-r border-[#27272A] bg-[#111114]"
      aria-label="Primary navigation"
    >
      {/* Logo */}
      <div className="flex items-center gap-2 px-5 py-5 border-b border-[#27272A]">
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
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-0.5" aria-label="Main menu">
        {navItems.map((item) => {
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

        {/* Admin-only nav items */}
        {isAdmin && (
          <Link
            href="/dashboard/feedback"
            aria-current={isActive("/dashboard/feedback") ? "page" : undefined}
            className={cn(
              "flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors duration-150",
              isActive("/dashboard/feedback")
                ? "bg-[rgba(45,212,191,0.08)] text-teal-400"
                : "text-[#A1A1AA] hover:text-[#FAFAFA] hover:bg-[#18181B]"
            )}
          >
            <MessageSquare
              className={cn(
                "w-4 h-4 shrink-0",
                isActive("/dashboard/feedback") ? "text-teal-400" : "text-[#71717A]"
              )}
              aria-hidden="true"
            />
            <span>Feedback</span>
          </Link>
        )}
      </nav>

      {/* Bottom: user + settings */}
      <div className="border-t border-[#27272A] p-3 space-y-0.5">
        <Link
          href="/dashboard/settings"
          className="flex items-center gap-3 px-3 py-2 rounded-md text-sm text-[#A1A1AA] hover:text-[#FAFAFA] hover:bg-[#18181B] transition-colors duration-150"
        >
          <Settings className="w-4 h-4 text-[#71717A]" aria-hidden="true" />
          <span>Settings</span>
        </Link>
        <div className="flex items-center gap-3 px-3 py-2 rounded-md">
          <div
            className="w-6 h-6 rounded-full bg-[#27272A] border border-[#3F3F46] flex items-center justify-center shrink-0"
            aria-hidden="true"
          >
            <User className="w-3.5 h-3.5 text-[#71717A]" />
          </div>
          <div className="min-w-0">
            <p className="text-xs font-medium text-[#FAFAFA] truncate">
              isaac@mnemora.dev
            </p>
            <p className="text-xs text-[#71717A] truncate">Free tier</p>
          </div>
        </div>
      </div>
    </aside>
  );
}
