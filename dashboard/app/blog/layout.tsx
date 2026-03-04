import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Blog — Mnemora",
  description:
    "Tutorials, architecture deep-dives, and comparisons for building AI agents with persistent memory.",
  openGraph: {
    title: "Blog — Mnemora",
    description:
      "Tutorials, architecture deep-dives, and comparisons for building AI agents with persistent memory.",
    type: "website",
    url: "https://mnemora.dev/blog",
  },
  twitter: {
    card: "summary_large_image",
    title: "Blog — Mnemora",
    description:
      "Tutorials, architecture deep-dives, and comparisons for building AI agents with persistent memory.",
  },
};

export default function BlogLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}
