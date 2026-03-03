"use client";

import { useSession, signOut } from "next-auth/react";
import Image from "next/image";
import { useState, useRef, useEffect } from "react";
import { LogOut, ChevronDown } from "lucide-react";
import { LoginButton } from "./login-button";

export function UserMenu() {
  const { data: session, status } = useSession();
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Close menu on outside click
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    if (open) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [open]);

  // Close menu on Escape
  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setOpen(false);
      }
    }
    if (open) {
      document.addEventListener("keydown", handleKeyDown);
    }
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [open]);

  if (status === "loading") {
    return (
      <div
        className="w-7 h-7 rounded-full bg-[#27272A] animate-pulse"
        aria-label="Loading user session"
      />
    );
  }

  if (status === "unauthenticated" || !session) {
    return <LoginButton />;
  }

  const { user } = session;
  const displayName = user.name ?? user.email ?? "User";
  const avatarUrl = user.image;

  function handleSignOut() {
    setOpen(false);
    signOut({ callbackUrl: "/" });
  }

  return (
    <div className="relative" ref={menuRef}>
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label={`User menu for ${displayName}`}
        className="flex items-center gap-2 px-2 py-1.5 rounded-md hover:bg-[#18181B] transition-colors duration-150 group"
      >
        {avatarUrl ? (
          <Image
            src={avatarUrl}
            alt={displayName}
            width={28}
            height={28}
            className="rounded-full border border-[#27272A]"
          />
        ) : (
          <div
            className="w-7 h-7 rounded-full bg-[#27272A] border border-[#3F3F46] flex items-center justify-center text-xs font-semibold text-[#A1A1AA]"
            aria-hidden="true"
          >
            {displayName.charAt(0).toUpperCase()}
          </div>
        )}
        <span className="text-sm text-[#A1A1AA] group-hover:text-[#FAFAFA] transition-colors duration-150 max-w-[120px] truncate hidden sm:block">
          {displayName}
        </span>
        <ChevronDown
          className={`w-3.5 h-3.5 text-[#71717A] transition-transform duration-150 ${open ? "rotate-180" : ""}`}
          aria-hidden="true"
        />
      </button>

      {open && (
        <div
          role="menu"
          aria-label="User options"
          className="absolute right-0 top-full mt-1.5 w-52 rounded-md border border-[#27272A] bg-[#111114] shadow-xl shadow-black/40 overflow-hidden z-50"
        >
          {/* User info */}
          <div className="px-3 py-2.5 border-b border-[#27272A]">
            <p className="text-xs font-medium text-[#FAFAFA] truncate">
              {displayName}
            </p>
            {user.email && (
              <p className="text-xs text-[#71717A] truncate mt-0.5">
                {user.email}
              </p>
            )}
          </div>

          {/* Actions */}
          <div className="py-1">
            <button
              type="button"
              role="menuitem"
              onClick={handleSignOut}
              className="flex w-full items-center gap-2.5 px-3 py-2 text-sm text-[#A1A1AA] hover:text-[#FAFAFA] hover:bg-[#18181B] transition-colors duration-150"
            >
              <LogOut className="w-3.5 h-3.5" aria-hidden="true" />
              Sign out
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
