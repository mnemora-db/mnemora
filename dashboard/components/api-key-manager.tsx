"use client";

import { useState, useEffect, useCallback } from "react";
import { Copy, Check, Plus, Trash2, Key, AlertTriangle } from "lucide-react";

interface KeyData {
  has_key: boolean;
  prefix?: string;
  tier?: string;
  created_at?: string;
}

export function ApiKeyManager() {
  const [keyData, setKeyData] = useState<KeyData | null>(null);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [revoking, setRevoking] = useState(false);
  const [plaintextKey, setPlaintextKey] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchKey = useCallback(async () => {
    try {
      const res = await fetch("/api/keys");
      if (!res.ok) throw new Error("Failed to fetch key");
      const data: KeyData = await res.json();
      setKeyData(data);
    } catch {
      setError("Failed to load API key data");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchKey();
  }, [fetchKey]);

  async function handleCreate() {
    setCreating(true);
    setError(null);
    try {
      const res = await fetch("/api/keys", { method: "POST" });
      if (!res.ok) throw new Error("Failed to create key");
      const data = await res.json();
      setPlaintextKey(data.key);
      setKeyData({
        has_key: true,
        prefix: data.prefix,
        tier: data.tier,
        created_at: data.created_at,
      });
    } catch {
      setError("Failed to create API key");
    } finally {
      setCreating(false);
    }
  }

  async function handleRevoke() {
    setRevoking(true);
    setError(null);
    try {
      const res = await fetch("/api/keys", { method: "DELETE" });
      if (!res.ok) throw new Error("Failed to revoke key");
      setKeyData({ has_key: false });
      setPlaintextKey(null);
    } catch {
      setError("Failed to revoke API key");
    } finally {
      setRevoking(false);
    }
  }

  async function handleCopy() {
    if (!plaintextKey) return;
    try {
      await navigator.clipboard.writeText(plaintextKey);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard API unavailable
    }
  }

  function formatDate(iso: string): string {
    const d = new Date(iso);
    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    if (diffDays === 0) return "Today";
    if (diffDays === 1) return "Yesterday";
    if (diffDays < 30) return `${diffDays} days ago`;
    return d.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  }

  if (loading) {
    return (
      <article
        className="rounded-md border border-[#27272A] bg-[#18181B] px-5 py-4"
        aria-label="API Key"
      >
        <p className="text-xs font-medium text-[#71717A] uppercase tracking-wide">
          API Key
        </p>
        <div className="mt-3 h-10 bg-[#111114] rounded-sm animate-pulse" />
      </article>
    );
  }

  // ── Plaintext key just created — show it once ──
  if (plaintextKey) {
    return (
      <article
        className="rounded-md border border-[#27272A] bg-[#18181B] px-5 py-4 flex flex-col gap-4"
        aria-label="API Key"
      >
        <div>
          <p className="text-xs font-medium text-[#71717A] uppercase tracking-wide">
            API Key
          </p>

          {/* Warning banner */}
          <div className="mt-3 flex items-start gap-2 rounded-sm border border-amber-500/30 bg-amber-500/5 px-3 py-2">
            <AlertTriangle
              className="w-4 h-4 text-amber-500 mt-0.5 shrink-0"
              aria-hidden="true"
            />
            <p className="text-xs text-amber-400">
              Copy this key now. It won&apos;t be shown again.
            </p>
          </div>

          {/* Key display */}
          <div className="mt-3 flex items-center gap-2">
            <code className="flex-1 font-mono text-sm text-[#2DD4BF] bg-[#111114] border border-[#27272A] rounded-sm px-3 py-2 truncate select-all">
              {plaintextKey}
            </code>
            <button
              onClick={handleCopy}
              aria-label={copied ? "Copied" : "Copy API key"}
              className="w-8 h-8 flex items-center justify-center rounded-sm border border-[#27272A] bg-[#111114] text-[#71717A] hover:text-[#FAFAFA] hover:border-[#3F3F46] transition-colors duration-150 shrink-0"
            >
              {copied ? (
                <Check
                  className="w-3.5 h-3.5 text-green-500"
                  aria-hidden="true"
                />
              ) : (
                <Copy className="w-3.5 h-3.5" aria-hidden="true" />
              )}
            </button>
          </div>
        </div>

        <button
          onClick={() => setPlaintextKey(null)}
          className="text-xs text-[#71717A] hover:text-[#A1A1AA] transition-colors duration-150 self-start"
        >
          Done — I&apos;ve saved the key
        </button>
      </article>
    );
  }

  // ── No key yet — show create button ──
  if (!keyData?.has_key) {
    return (
      <article
        className="rounded-md border border-[#27272A] bg-[#18181B] px-5 py-4 flex flex-col gap-4"
        aria-label="API Key"
      >
        <div>
          <p className="text-xs font-medium text-[#71717A] uppercase tracking-wide">
            API Key
          </p>
          <p className="mt-2 text-sm text-[#A1A1AA]">
            Generate an API key to start using the Mnemora API.
          </p>
        </div>

        {error && <p className="text-xs text-red-400">{error}</p>}

        <button
          onClick={handleCreate}
          disabled={creating}
          className="flex items-center gap-1.5 self-start px-3.5 py-2 rounded-md bg-[#2DD4BF] text-[#09090B] text-sm font-semibold hover:bg-[#2DD4BF]/90 transition-colors duration-150 disabled:opacity-50"
        >
          <Plus className="w-3.5 h-3.5" aria-hidden="true" />
          {creating ? "Generating..." : "Generate API Key"}
        </button>
      </article>
    );
  }

  // ── Key exists — show masked key + metadata ──
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
            <Key
              className="w-3.5 h-3.5 inline mr-2 text-[#71717A]"
              aria-hidden="true"
            />
            {keyData.prefix}...****
          </code>
        </div>
      </div>

      {error && <p className="text-xs text-red-400">{error}</p>}

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3 text-xs text-[#71717A]">
          {keyData.created_at && (
            <span>Created {formatDate(keyData.created_at)}</span>
          )}
          <span className="px-1.5 py-0.5 rounded bg-[#111114] border border-[#27272A] text-[#A1A1AA] uppercase text-[10px] font-medium tracking-wide">
            {keyData.tier}
          </span>
        </div>

        <button
          onClick={handleRevoke}
          disabled={revoking}
          className="flex items-center gap-1.5 h-7 px-2.5 text-xs rounded-sm border border-[#3F3F46] bg-transparent text-red-500 hover:text-red-400 hover:border-red-500/50 hover:bg-red-500/5 transition-colors duration-150 disabled:opacity-50"
        >
          <Trash2 className="w-3 h-3" aria-hidden="true" />
          {revoking ? "Revoking..." : "Revoke"}
        </button>
      </div>
    </article>
  );
}
