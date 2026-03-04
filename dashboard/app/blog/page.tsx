import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { getAllPosts } from "@/lib/blog";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Blog — Mnemora",
  description:
    "Tutorials, architecture deep-dives, and comparisons for building AI agents with persistent memory.",
  alternates: { canonical: "https://mnemora.dev/blog" },
};

const TAG_COLORS: Record<string, string> = {
  tutorial: "border-[#2DD4BF]/30 bg-[#2DD4BF]/[0.08] text-[#2DD4BF]",
  comparison: "border-[#38BDF8]/30 bg-[#38BDF8]/[0.08] text-[#38BDF8]",
  architecture: "border-[#A78BFA]/30 bg-[#A78BFA]/[0.08] text-[#A78BFA]",
  concepts: "border-[#FB923C]/30 bg-[#FB923C]/[0.08] text-[#FB923C]",
  python: "border-[#2DD4BF]/30 bg-[#2DD4BF]/[0.08] text-[#2DD4BF]",
  "getting-started":
    "border-[#2DD4BF]/30 bg-[#2DD4BF]/[0.08] text-[#2DD4BF]",
  langgraph: "border-[#38BDF8]/30 bg-[#38BDF8]/[0.08] text-[#38BDF8]",
  integration: "border-[#38BDF8]/30 bg-[#38BDF8]/[0.08] text-[#38BDF8]",
  aws: "border-[#FB923C]/30 bg-[#FB923C]/[0.08] text-[#FB923C]",
  "deep-dive": "border-[#A78BFA]/30 bg-[#A78BFA]/[0.08] text-[#A78BFA]",
  saas: "border-[#FB923C]/30 bg-[#FB923C]/[0.08] text-[#FB923C]",
  "multi-tenant":
    "border-[#A78BFA]/30 bg-[#A78BFA]/[0.08] text-[#A78BFA]",
};

function formatDate(iso: string): string {
  return new Date(iso + "T00:00:00").toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

export default function BlogIndexPage() {
  const posts = getAllPosts();

  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "Blog",
    name: "Mnemora Blog",
    description:
      "Tutorials, architecture deep-dives, and comparisons for building AI agents with persistent memory.",
    url: "https://mnemora.dev/blog",
    publisher: {
      "@type": "Organization",
      name: "Mnemora",
      url: "https://mnemora.dev",
    },
    blogPost: posts.map((post) => ({
      "@type": "BlogPosting",
      headline: post.title,
      description: post.excerpt,
      datePublished: post.date,
      author: { "@type": "Person", name: post.author },
      url: `https://mnemora.dev/blog/${post.slug}`,
    })),
  };

  return (
    <div className="min-h-screen bg-[#09090B] text-[#FAFAFA]">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />

      {/* Header */}
      <header className="border-b border-[#27272A] bg-[#09090B]/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-4xl mx-auto px-4 h-14 flex items-center justify-between">
          <Link
            href="/"
            className="text-sm font-semibold text-[#FAFAFA] tracking-tight hover:text-[#2DD4BF] transition-colors"
          >
            mnemora
          </Link>
          <nav className="flex items-center gap-6">
            <Link
              href="/docs/quickstart"
              className="text-xs text-[#71717A] hover:text-[#FAFAFA] transition-colors"
            >
              Docs
            </Link>
            <Link
              href="/blog"
              className="text-xs text-[#2DD4BF] font-medium"
            >
              Blog
            </Link>
            <Link
              href="/dashboard"
              className="text-xs text-[#71717A] hover:text-[#FAFAFA] transition-colors"
            >
              Dashboard
            </Link>
          </nav>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-16">
        {/* Page title */}
        <div className="mb-12">
          <Link
            href="/"
            className="inline-flex items-center gap-1.5 text-xs text-[#52525B] hover:text-[#A1A1AA] transition-colors mb-6"
          >
            <ArrowLeft className="w-3 h-3" />
            Home
          </Link>
          <h1 className="text-3xl sm:text-4xl font-bold tracking-tight">
            Blog
          </h1>
          <p className="mt-3 text-[#71717A] text-sm max-w-lg">
            Tutorials, architecture deep-dives, and comparisons for building AI
            agents with persistent memory.
          </p>
        </div>

        {/* Posts grid */}
        <div className="space-y-4">
          {posts.map((post) => (
            <Link
              key={post.slug}
              href={`/blog/${post.slug}`}
              className="group block rounded-xl border border-[#27272A] bg-[#111114] p-6 hover:border-[#3F3F46] hover:bg-[#18181B] transition-all duration-200"
            >
              <div className="flex items-center gap-2 mb-3">
                {post.tags.slice(0, 2).map((tag) => (
                  <span
                    key={tag}
                    className={`text-[10px] font-semibold px-2 py-0.5 rounded border ${
                      TAG_COLORS[tag] ?? TAG_COLORS.tutorial
                    }`}
                  >
                    {tag}
                  </span>
                ))}
                <span className="text-[10px] text-[#52525B] ml-auto">
                  {post.readingTime} read
                </span>
              </div>
              <h2 className="text-lg font-semibold text-[#FAFAFA] group-hover:text-[#2DD4BF] transition-colors mb-2">
                {post.title}
              </h2>
              <p className="text-sm text-[#71717A] leading-relaxed mb-3">
                {post.excerpt}
              </p>
              <div className="flex items-center gap-2 text-xs text-[#52525B]">
                <span>{formatDate(post.date)}</span>
                <span>·</span>
                <span>{post.author}</span>
              </div>
            </Link>
          ))}
        </div>
      </main>
    </div>
  );
}
