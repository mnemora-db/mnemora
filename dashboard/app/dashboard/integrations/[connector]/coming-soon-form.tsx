"use client";

import { useState } from "react";
import { toast } from "sonner";

export function ComingSoonForm({ connectorName }: { connectorName: string }) {
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!email.trim()) return;
    setSubmitting(true);
    try {
      await fetch("/api/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          type: "feature",
          title: `Integration interest: ${connectorName}`,
          description: `User wants ${connectorName} integration. Email: ${email}`,
        }),
      });
      toast.success(`We'll notify you when ${connectorName} is ready!`);
      setEmail("");
    } catch {
      toast.error("Something went wrong");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex gap-2 max-w-sm mx-auto">
      <input
        type="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        placeholder="you@company.com"
        required
        className="flex-1 rounded-md border border-[#3F3F46] bg-[#09090B] px-3 py-2 text-sm text-[#FAFAFA] placeholder:text-[#52525B] focus:outline-none focus:border-[#2DD4BF] transition-colors"
      />
      <button
        type="submit"
        disabled={submitting}
        className="rounded-md bg-[#2DD4BF] px-4 py-2 text-sm font-medium text-[#09090B] hover:bg-teal-300 transition-colors disabled:opacity-50"
      >
        {submitting ? "..." : "Notify Me"}
      </button>
    </form>
  );
}
