import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { notFound } from "next/navigation";
import { getPost, getAllPosts } from "@/lib/blog";
import { MarkdownRenderer } from "@/components/docs/markdown-renderer";
import { ShareButtons } from "./share-buttons";
import type { Metadata } from "next";

// ── Static params for SSG ────────────────────────────────────────────
export function generateStaticParams() {
  return getAllPosts().map((post) => ({ slug: post.slug }));
}

// ── Dynamic metadata per post ────────────────────────────────────────
export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const post = getPost(slug);
  if (!post) return { title: "Post Not Found — Mnemora" };

  return {
    title: `${post.title} — Mnemora Blog`,
    description: post.excerpt,
    keywords: post.keywords,
    authors: [{ name: post.author }],
    alternates: { canonical: `https://mnemora.dev/blog/${post.slug}` },
    openGraph: {
      title: post.title,
      description: post.excerpt,
      type: "article",
      url: `https://mnemora.dev/blog/${post.slug}`,
      publishedTime: post.date,
      authors: [post.author],
      tags: post.tags,
    },
    twitter: {
      card: "summary_large_image",
      title: post.title,
      description: post.excerpt,
    },
  };
}

// ── Helpers ──────────────────────────────────────────────────────────
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

// ── Page component ───────────────────────────────────────────────────
export default async function BlogPostPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const post = getPost(slug);
  if (!post) notFound();

  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "Article",
    headline: post.title,
    description: post.excerpt,
    datePublished: post.date,
    author: {
      "@type": "Person",
      name: post.author,
    },
    publisher: {
      "@type": "Organization",
      name: "Mnemora",
      url: "https://mnemora.dev",
    },
    url: `https://mnemora.dev/blog/${post.slug}`,
    keywords: post.keywords.join(", "),
    mainEntityOfPage: {
      "@type": "WebPage",
      "@id": `https://mnemora.dev/blog/${post.slug}`,
    },
  };

  return (
    <div className="min-h-screen bg-[#09090B] text-[#FAFAFA]">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />

      {/* Header */}
      <header className="border-b border-[#27272A] bg-[#09090B]/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-3xl mx-auto px-4 h-14 flex items-center justify-between">
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

      <main className="max-w-3xl mx-auto px-4 py-16">
        {/* Back link */}
        <Link
          href="/blog"
          className="inline-flex items-center gap-1.5 text-xs text-[#52525B] hover:text-[#A1A1AA] transition-colors mb-8"
        >
          <ArrowLeft className="w-3 h-3" />
          All posts
        </Link>

        {/* Post header */}
        <header className="mb-10">
          <div className="flex items-center gap-2 mb-4">
            {post.tags.map((tag) => (
              <span
                key={tag}
                className={`text-[10px] font-semibold px-2 py-0.5 rounded border ${
                  TAG_COLORS[tag] ?? TAG_COLORS.tutorial
                }`}
              >
                {tag}
              </span>
            ))}
          </div>
          <h1 className="text-3xl sm:text-4xl font-bold tracking-tight leading-tight mb-4">
            {post.title}
          </h1>
          <div className="flex items-center gap-3 text-sm text-[#71717A]">
            <span>{post.author}</span>
            <span className="text-[#3F3F46]">·</span>
            <time dateTime={post.date}>{formatDate(post.date)}</time>
            <span className="text-[#3F3F46]">·</span>
            <span>{post.readingTime} read</span>
          </div>
        </header>

        {/* Post content */}
        <article className="prose-mnemora">
          <MarkdownRenderer content={post.content} />
        </article>

        {/* Share + back */}
        <footer className="mt-16 pt-8 border-t border-[#27272A]">
          <div className="flex items-center justify-between">
            <Link
              href="/blog"
              className="text-sm text-[#2DD4BF] hover:underline"
            >
              &larr; All posts
            </Link>
            <ShareButtons
              title={post.title}
              url={`https://mnemora.dev/blog/${post.slug}`}
            />
          </div>
        </footer>
      </main>
    </div>
  );
}
