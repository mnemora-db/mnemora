import Link from "next/link";
import {
  Rocket,
  BookOpen,
  Code2,
  Puzzle,
  CreditCard,
} from "lucide-react";

const sections = [
  {
    title: "Quickstart",
    description: "Store your first memory in under 5 minutes.",
    href: "/docs/quickstart",
    icon: Rocket,
  },
  {
    title: "Core Concepts",
    description:
      "Understand the four memory types: working, semantic, episodic, and procedural.",
    href: "/docs/concepts",
    icon: BookOpen,
  },
  {
    title: "API Reference",
    description: "All 19 endpoints — authentication, request format, error codes.",
    href: "/docs/api-reference",
    icon: Code2,
  },
  {
    title: "Integrations",
    description: "Drop-in support for LangGraph, LangChain, and CrewAI.",
    href: "/docs/integrations/langgraph",
    icon: Puzzle,
  },
  {
    title: "Pricing",
    description: "Free tier, paid plans, and what counts as an API call.",
    href: "/docs/pricing",
    icon: CreditCard,
  },
];

export default function DocsOverview() {
  return (
    <div className="space-y-10">
      {/* Header */}
      <div>
        <h1 className="text-[28px] font-bold text-[#FAFAFA] tracking-tight">
          Mnemora Documentation
        </h1>
        <p className="mt-2 text-[#71717A] text-[15px] leading-relaxed max-w-xl">
          One API for four memory types. Give your AI agents persistent memory
          backed by DynamoDB, Aurora pgvector, and S3.
        </p>
      </div>

      {/* Quick links grid */}
      <section aria-label="Documentation sections">
        <div className="grid gap-3 sm:grid-cols-2">
          {sections.map((s) => (
            <Link
              key={s.href}
              href={s.href}
              className="group rounded-lg border border-[#27272A] bg-[#18181B] p-5 hover:border-[#3F3F46] transition-colors duration-150"
            >
              <div className="flex items-center gap-3 mb-2">
                <div className="w-8 h-8 rounded-md bg-[#111114] border border-[#27272A] flex items-center justify-center">
                  <s.icon
                    className="w-4 h-4 text-[#2DD4BF]"
                    aria-hidden="true"
                  />
                </div>
                <h2 className="text-sm font-semibold text-[#FAFAFA] group-hover:text-[#2DD4BF] transition-colors duration-150">
                  {s.title}
                </h2>
              </div>
              <p className="text-xs text-[#71717A] leading-relaxed">
                {s.description}
              </p>
            </Link>
          ))}
        </div>
      </section>

      {/* Getting started callout */}
      <section className="rounded-lg border border-[#27272A] bg-[#111114] p-6">
        <h2 className="text-sm font-semibold text-[#FAFAFA] mb-2">
          New to Mnemora?
        </h2>
        <p className="text-xs text-[#71717A] leading-relaxed mb-4">
          Start with the quickstart guide — install the SDK, store a memory, and
          run a vector search in under 5 minutes.
        </p>
        <Link
          href="/docs/quickstart"
          className="inline-flex items-center gap-2 px-4 py-2 rounded-md bg-[#2DD4BF] text-[#09090B] text-xs font-semibold hover:bg-[#2DD4BF]/90 transition-colors duration-150"
        >
          <Rocket className="w-3.5 h-3.5" aria-hidden="true" />
          Get started
        </Link>
      </section>
    </div>
  );
}
