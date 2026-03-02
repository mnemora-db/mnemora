import { ApiKeyCard } from "@/components/api-key-card";
import { ShieldCheck } from "lucide-react";

export default function ApiKeysPage() {
  return (
    <div className="space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-[22px] font-semibold text-[#FAFAFA] tracking-tight">
          API Keys
        </h1>
        <p className="mt-0.5 text-sm text-[#71717A]">
          Manage authentication credentials for your Mnemora workspace.
        </p>
      </div>

      {/* Key info note */}
      <div className="flex items-start gap-3 rounded-md border border-[#27272A] bg-[#111114] px-4 py-3">
        <ShieldCheck
          className="w-4 h-4 text-teal-400 mt-0.5 shrink-0"
          aria-hidden="true"
        />
        <p className="text-sm text-[#A1A1AA]">
          API keys are hashed with SHA-256 before storage. The full key is only
          shown once at creation time. Include your key in the{" "}
          <code className="font-mono text-xs text-[#FAFAFA] bg-[#27272A] px-1 py-0.5 rounded-sm">
            Authorization: Bearer &lt;key&gt;
          </code>{" "}
          header with every request.
        </p>
      </div>

      {/* Active key */}
      <section aria-label="Active API keys">
        <h2 className="text-xs font-medium text-[#71717A] uppercase tracking-wide mb-3">
          Active Keys
        </h2>
        <div className="max-w-xl">
          <ApiKeyCard
            maskedKey="mnm_****...****7f3a"
            createdLabel="5 days ago"
          />
        </div>
      </section>
    </div>
  );
}
