"use client";

import { useSession, signIn } from "next-auth/react";
import Link from "next/link";
import { ArrowRight } from "lucide-react";

export function HeroCtaButton() {
  const { data: session, status } = useSession();

  if (status === "loading") {
    return (
      <div
        className="flex items-center gap-2 px-6 py-3 rounded-lg bg-[#2DD4BF]/20 text-transparent text-sm font-semibold select-none"
        aria-hidden="true"
      >
        Get started free
        <ArrowRight className="w-4 h-4" />
      </div>
    );
  }

  if (session) {
    return (
      <Link
        href="/dashboard"
        className="flex items-center gap-2 px-6 py-3 rounded-lg bg-[#2DD4BF] text-[#09090B] text-sm font-semibold hover:bg-[#2DD4BF]/90 transition-all duration-150 shadow-lg shadow-[#2DD4BF]/20"
      >
        Go to Dashboard
        <ArrowRight className="w-4 h-4" />
      </Link>
    );
  }

  return (
    <button
      type="button"
      onClick={() => signIn("github", { callbackUrl: "/dashboard" })}
      className="flex items-center gap-2 px-6 py-3 rounded-lg bg-[#2DD4BF] text-[#09090B] text-sm font-semibold hover:bg-[#2DD4BF]/90 transition-all duration-150 shadow-lg shadow-[#2DD4BF]/20"
    >
      Get started free
      <ArrowRight className="w-4 h-4" />
    </button>
  );
}
