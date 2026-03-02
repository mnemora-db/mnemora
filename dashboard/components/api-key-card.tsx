"use client";

import { useState } from "react";
import { Copy, Check, RefreshCw, Clock } from "lucide-react";
import { Button } from "@/components/ui/button";

interface ApiKeyCardProps {
  maskedKey: string;
  createdLabel: string;
}

export function ApiKeyCard({ maskedKey, createdLabel }: ApiKeyCardProps) {
  const [copied, setCopied] = useState(false);
  const [regenerating, setRegenerating] = useState(false);

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(maskedKey);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard API unavailable — no-op
    }
  }

  function handleRegenerate() {
    setRegenerating(true);
    // Stub: would call API to regenerate key
    setTimeout(() => setRegenerating(false), 1500);
  }

  return (
    <article
      className="rounded-md border border-[#27272A] bg-[#18181B] px-5 py-4 flex flex-col gap-4"
      aria-label="API Key"
    >
      <div>
        <p className="text-xs font-medium text-[#71717A] uppercase tracking-wide">
          API Key
        </p>
        <div className="mt-3 flex items-center gap-2">
          <code className="flex-1 font-mono text-sm text-[#FAFAFA] bg-[#111114] border border-[#27272A] rounded-sm px-3 py-2 truncate">
            {maskedKey}
          </code>
          <button
            onClick={handleCopy}
            aria-label={copied ? "Copied" : "Copy API key"}
            className="w-8 h-8 flex items-center justify-center rounded-sm border border-[#27272A] bg-[#111114] text-[#71717A] hover:text-[#FAFAFA] hover:border-[#3F3F46] transition-colors duration-150 shrink-0"
          >
            {copied ? (
              <Check className="w-3.5 h-3.5 text-green-500" aria-hidden="true" />
            ) : (
              <Copy className="w-3.5 h-3.5" aria-hidden="true" />
            )}
          </button>
        </div>
      </div>

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5 text-xs text-[#71717A]">
          <Clock className="w-3.5 h-3.5" aria-hidden="true" />
          <span>Created {createdLabel}</span>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={handleRegenerate}
          disabled={regenerating}
          aria-label="Regenerate API key"
          className="h-7 text-xs border-[#3F3F46] bg-transparent text-red-500 hover:text-red-400 hover:border-red-500/50 hover:bg-red-500/5 transition-colors duration-150"
        >
          <RefreshCw
            className={`w-3 h-3 mr-1.5 ${regenerating ? "animate-spin" : ""}`}
            aria-hidden="true"
          />
          {regenerating ? "Regenerating..." : "Regenerate"}
        </Button>
      </div>
    </article>
  );
}
