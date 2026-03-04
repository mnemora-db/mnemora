"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Bot,
  BarChart2,
  KeyRound,
  BookOpen,
  CreditCard,
  Settings,
  User,
  ShieldCheck,
  Menu,
  X,
} from "lucide-react";
import Image from "next/image";
import { useSession } from "next-auth/react";
import { useState, useEffect } from "react";
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
  { label: "Billing", href: "/dashboard/billing", icon: CreditCard },
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
  const [tier, setTier] = useState("free");
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    fetch("/api/keys")
      .then((r) => r.json())
      .then((data) => {
        if (data.tier) setTier(data.tier);
      })
      .catch(() => {});
  }, []);

  // Close mobile sidebar on route change
  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  // Prevent body scroll when mobile sidebar is open
  useEffect(() => {
    if (mobileOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [mobileOpen]);

  function isActive(href: string): boolean {
    if (href === "/dashboard") {
      return pathname === "/dashboard";
    }
    return pathname.startsWith(href);
  }

  const sidebarContent = (
    <>
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

        {/* Mobile close button */}
        <button
          onClick={() => setMobileOpen(false)}
          className="ml-auto md:hidden w-8 h-8 flex items-center justify-center rounded-md text-[#71717A] hover:text-[#FAFAFA] hover:bg-[#18181B] transition-colors duration-150"
          aria-label="Close menu"
        >
          <X className="w-4 h-4" />
        </button>
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
            href="/dashboard/admin"
            aria-current={isActive("/dashboard/admin") ? "page" : undefined}
            className={cn(
              "flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors duration-150",
              isActive("/dashboard/admin")
                ? "bg-[rgba(45,212,191,0.08)] text-teal-400"
                : "text-[#A1A1AA] hover:text-[#FAFAFA] hover:bg-[#18181B]"
            )}
          >
            <ShieldCheck
              className={cn(
                "w-4 h-4 shrink-0",
                isActive("/dashboard/admin") ? "text-teal-400" : "text-[#71717A]"
              )}
              aria-hidden="true"
            />
            <span>Admin</span>
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
          {session?.user?.image ? (
            <Image
              src={session.user.image}
              alt={session.user.name ?? "User"}
              width={24}
              height={24}
              className="rounded-full border border-[#3F3F46] shrink-0"
            />
          ) : (
            <div
              className="w-6 h-6 rounded-full bg-[#27272A] border border-[#3F3F46] flex items-center justify-center shrink-0"
              aria-hidden="true"
            >
              <User className="w-3.5 h-3.5 text-[#71717A]" />
            </div>
          )}
          <div className="min-w-0">
            <p className="text-xs font-medium text-[#FAFAFA] truncate">
              {session?.user?.email ?? ""}
            </p>
            <p className="text-xs text-[#71717A] truncate capitalize">
              {tier} tier
            </p>
          </div>
        </div>
      </div>
    </>
  );

  return (
    <>
      {/* Mobile hamburger button */}
      <button
        onClick={() => setMobileOpen(true)}
        className="fixed top-3 left-3 z-50 md:hidden w-10 h-10 flex items-center justify-center rounded-md bg-[#111114] border border-[#27272A] text-[#A1A1AA] hover:text-[#FAFAFA] hover:border-[#3F3F46] transition-colors duration-150"
        aria-label="Open menu"
      >
        <Menu className="w-5 h-5" />
      </button>

      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 md:hidden"
          onClick={() => setMobileOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Mobile sidebar */}
      <aside
        className={cn(
          "fixed left-0 top-0 h-screen w-60 flex flex-col border-r border-[#27272A] bg-[#111114] z-50 md:hidden transition-transform duration-200 ease-in-out",
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        )}
        aria-label="Primary navigation"
      >
        {sidebarContent}
      </aside>

      {/* Desktop sidebar */}
      <aside
        className="hidden md:flex fixed left-0 top-0 h-screen w-60 flex-col border-r border-[#27272A] bg-[#111114]"
        aria-label="Primary navigation"
      >
        {sidebarContent}
      </aside>
    </>
  );
}
