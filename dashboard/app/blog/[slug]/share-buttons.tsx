"use client";

import { useState } from "react";
import { Twitter, Linkedin, Link2, Check } from "lucide-react";

interface ShareButtonsProps {
  title: string;
  url: string;
}

export function ShareButtons({ title, url }: ShareButtonsProps) {
  const [copied, setCopied] = useState(false);

  async function copyLink() {
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback for older browsers
      const input = document.createElement("input");
      input.value = url;
      document.body.appendChild(input);
      input.select();
      document.execCommand("copy");
      document.body.removeChild(input);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }

  const twitterUrl = `https://twitter.com/intent/tweet?text=${encodeURIComponent(title)}&url=${encodeURIComponent(url)}`;
  const linkedinUrl = `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(url)}`;

  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-[#52525B] mr-1">Share</span>
      <a
        href={twitterUrl}
        target="_blank"
        rel="noopener noreferrer"
        className="w-8 h-8 rounded-md border border-[#27272A] bg-[#18181B] flex items-center justify-center hover:border-[#3F3F46] hover:bg-[#1C1C1F] transition-all duration-150"
        aria-label="Share on Twitter"
      >
        <Twitter className="w-3.5 h-3.5 text-[#71717A]" />
      </a>
      <a
        href={linkedinUrl}
        target="_blank"
        rel="noopener noreferrer"
        className="w-8 h-8 rounded-md border border-[#27272A] bg-[#18181B] flex items-center justify-center hover:border-[#3F3F46] hover:bg-[#1C1C1F] transition-all duration-150"
        aria-label="Share on LinkedIn"
      >
        <Linkedin className="w-3.5 h-3.5 text-[#71717A]" />
      </a>
      <button
        onClick={copyLink}
        className="w-8 h-8 rounded-md border border-[#27272A] bg-[#18181B] flex items-center justify-center hover:border-[#3F3F46] hover:bg-[#1C1C1F] transition-all duration-150"
        aria-label="Copy link"
      >
        {copied ? (
          <Check className="w-3.5 h-3.5 text-[#2DD4BF]" />
        ) : (
          <Link2 className="w-3.5 h-3.5 text-[#71717A]" />
        )}
      </button>
    </div>
  );
}
