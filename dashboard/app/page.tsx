import Link from "next/link";
import { Github } from "lucide-react";

export default function LoginPage() {
  return (
    <main
      className="min-h-screen bg-[#09090B] flex items-center justify-center px-4"
      aria-label="Mnemora sign in"
    >
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="flex flex-col items-center mb-8">
          <div
            className="w-10 h-10 rounded-md flex items-center justify-center bg-[#18181B] border border-[#27272A] mb-4"
            aria-hidden="true"
          >
            <svg
              width="20"
              height="20"
              viewBox="0 0 20 20"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                d="M3 16V4L10 11L17 4V16"
                stroke="#2DD4BF"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </div>
          <h1 className="text-xl font-semibold text-[#FAFAFA] tracking-tight">
            mnemora
          </h1>
          <p className="mt-1.5 text-sm text-[#71717A] text-center">
            Memory for AI Agents
          </p>
        </div>

        {/* Sign in card */}
        <div className="rounded-md border border-[#27272A] bg-[#111114] px-6 py-6">
          <h2 className="text-base font-semibold text-[#FAFAFA] mb-1">
            Sign in to your account
          </h2>
          <p className="text-sm text-[#71717A] mb-5">
            Use your GitHub account to continue.
          </p>

          <Link
            href="/dashboard"
            className="flex items-center justify-center gap-2.5 w-full h-9 rounded-sm border border-teal-400/40 bg-teal-400/5 text-teal-400 text-sm font-medium hover:bg-teal-400/10 hover:border-teal-400/60 transition-colors duration-150 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-teal-400"
            aria-label="Sign in with GitHub"
          >
            <Github className="w-4 h-4" aria-hidden="true" />
            Sign in with GitHub
          </Link>

          <p className="mt-4 text-xs text-[#52525B] text-center">
            By signing in, you agree to our{" "}
            <a
              href="#"
              className="text-[#71717A] hover:text-teal-400 transition-colors duration-150 underline underline-offset-2"
            >
              Terms of Service
            </a>{" "}
            and{" "}
            <a
              href="#"
              className="text-[#71717A] hover:text-teal-400 transition-colors duration-150 underline underline-offset-2"
            >
              Privacy Policy
            </a>
            .
          </p>
        </div>

        {/* Tagline */}
        <p className="mt-8 text-center text-xs text-[#52525B] leading-relaxed">
          One API. Four memory types. Zero infrastructure.
        </p>
      </div>
    </main>
  );
}
