"use client";

import { useState } from "react";
import { Copy, Check } from "lucide-react";

export function CodeBlock({ code }: { code: string }) {
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(code.trim());
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard API unavailable
    }
  }

  return (
    <div className="relative group">
      <pre className="px-4 py-3 bg-[#111114] border border-[#27272A] rounded-md text-xs font-mono text-[#A1A1AA] overflow-x-auto">
        <code>{code}</code>
      </pre>
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
    </div>
  );
}
