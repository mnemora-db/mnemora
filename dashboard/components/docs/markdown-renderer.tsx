"use client";

import { useState, type ReactNode } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import { Copy, Check } from "lucide-react";

interface MarkdownRendererProps {
  content: string;
}

function extractText(node: ReactNode): string {
  if (typeof node === "string") return node;
  if (typeof node === "number") return String(node);
  if (!node) return "";
  if (Array.isArray(node)) return node.map(extractText).join("");
  if (typeof node === "object" && "props" in node) {
    return extractText(node.props.children);
  }
  return "";
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard API unavailable
    }
  }

  return (
    <button
      onClick={handleCopy}
      className="absolute top-2 right-2 w-7 h-7 flex items-center justify-center rounded-md border border-[#27272A] bg-[#111114] text-[#71717A] hover:text-[#FAFAFA] hover:border-[#3F3F46] transition-colors duration-150 opacity-0 group-hover:opacity-100"
      aria-label={copied ? "Copied" : "Copy code"}
    >
      {copied ? (
        <Check className="w-3.5 h-3.5 text-green-500" />
      ) : (
        <Copy className="w-3.5 h-3.5" />
      )}
    </button>
  );
}

export function MarkdownRenderer({ content }: MarkdownRendererProps) {
  return (
    <article className="prose-mnemora">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeHighlight]}
        components={{
          pre({ children }) {
            const text = extractText(children);
            return (
              <div className="relative group">
                <pre>{children}</pre>
                <CopyButton text={text} />
              </div>
            );
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </article>
  );
}
