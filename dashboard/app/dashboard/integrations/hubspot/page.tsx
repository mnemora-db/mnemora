"use client";

import { useState } from "react";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { Check, Loader2, ArrowRight } from "lucide-react";
import { toast } from "sonner";

const STEPS = ["Token", "Objects", "Sync", "Done"];
const OBJECT_OPTIONS = ["contacts", "companies", "deals", "tickets"];

export default function HubSpotSetupPage() {
  const [step, setStep] = useState(0);
  const [token, setToken] = useState("");
  const [testing, setTesting] = useState(false);
  const [objects, setObjects] = useState<string[]>([...OBJECT_OPTIONS]);
  const [counts, setCounts] = useState<Record<string, number>>({});

  async function testConnection() {
    if (!token.trim()) {
      toast.error("Enter your HubSpot Private App token");
      return;
    }
    setTesting(true);
    try {
      const res = await fetch("/api/integrations/hubspot", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "test", token }),
      });
      const data = await res.json();
      if (data.success) {
        toast.success("Connected to HubSpot!");
        setStep(1);
      } else {
        toast.error(data.error || "Connection failed");
      }
    } catch {
      toast.error("Connection failed");
    } finally {
      setTesting(false);
    }
  }

  function toggleObject(obj: string) {
    setObjects((prev) =>
      prev.includes(obj) ? prev.filter((o) => o !== obj) : [...prev, obj]
    );
  }

  async function startSync() {
    setStep(2);
    try {
      const res = await fetch("/api/integrations/hubspot", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "sync", token, objects }),
      });
      const data = await res.json();
      if (data.success) {
        setCounts(data.counts || {});
        setStep(3);
        toast.success("Sync complete!");
      } else {
        toast.error(data.error || "Sync failed");
        setStep(1);
      }
    } catch {
      toast.error("Sync failed");
      setStep(1);
    } finally {
      // sync complete
    }
  }

  return (
    <div className="max-w-lg mx-auto space-y-8">
      <div>
        <h1 className="text-[22px] font-semibold text-[#FAFAFA] tracking-tight">
          🟠 Connect HubSpot
        </h1>
        <p className="text-sm text-[#A1A1AA] mt-1">
          Sync your CRM data to Mnemora for agent memory.
        </p>
      </div>

      {/* Step indicators */}
      <div className="flex items-center gap-2">
        {STEPS.map((label, i) => (
          <div key={label} className="flex items-center gap-2">
            <div
              className={cn(
                "w-7 h-7 rounded-full flex items-center justify-center text-xs font-semibold border",
                i < step
                  ? "bg-teal-500/20 border-teal-500/40 text-teal-400"
                  : i === step
                    ? "bg-[#27272A] border-[#3F3F46] text-[#FAFAFA]"
                    : "bg-[#18181B] border-[#27272A] text-[#52525B]"
              )}
            >
              {i < step ? <Check className="w-3.5 h-3.5" /> : i + 1}
            </div>
            <span
              className={cn(
                "text-xs",
                i <= step ? "text-[#A1A1AA]" : "text-[#52525B]"
              )}
            >
              {label}
            </span>
            {i < STEPS.length - 1 && (
              <div className="w-6 h-px bg-[#27272A]" />
            )}
          </div>
        ))}
      </div>

      {/* Step content */}
      <div className="rounded-xl border border-[#27272A] bg-[#18181B] p-6 space-y-5">
        {step === 0 && (
          <>
            <div>
              <label className="block text-sm font-medium text-[#FAFAFA] mb-2">
                HubSpot Private App Token
              </label>
              <input
                type="password"
                value={token}
                onChange={(e) => setToken(e.target.value)}
                placeholder="pat-na1-..."
                className="w-full rounded-md border border-[#3F3F46] bg-[#09090B] px-3 py-2 text-sm text-[#FAFAFA] placeholder:text-[#52525B] focus:outline-none focus:border-[#2DD4BF] transition-colors"
              />
              <p className="text-xs text-[#71717A] mt-2">
                Settings → Integrations → Private Apps → Create a private app
                with CRM scopes.
              </p>
            </div>
            <button
              onClick={testConnection}
              disabled={testing}
              className="inline-flex items-center gap-2 rounded-md bg-[#2DD4BF] px-4 py-2 text-sm font-medium text-[#09090B] hover:bg-teal-300 transition-colors disabled:opacity-50"
            >
              {testing && <Loader2 className="w-4 h-4 animate-spin" />}
              {testing ? "Testing..." : "Test Connection"}
            </button>
          </>
        )}

        {step === 1 && (
          <>
            <div>
              <p className="text-sm font-medium text-[#FAFAFA] mb-3">
                Select objects to sync
              </p>
              <div className="space-y-2">
                {OBJECT_OPTIONS.map((obj) => (
                  <label
                    key={obj}
                    className="flex items-center gap-3 px-3 py-2 rounded-md hover:bg-[#111114] cursor-pointer transition-colors"
                  >
                    <input
                      type="checkbox"
                      checked={objects.includes(obj)}
                      onChange={() => toggleObject(obj)}
                      className="rounded border-[#3F3F46] bg-[#09090B] text-teal-400 focus:ring-teal-400 focus:ring-offset-0"
                    />
                    <span className="text-sm text-[#FAFAFA] capitalize">
                      {obj}
                    </span>
                  </label>
                ))}
              </div>
            </div>
            <button
              onClick={startSync}
              disabled={objects.length === 0}
              className="inline-flex items-center gap-2 rounded-md bg-[#2DD4BF] px-4 py-2 text-sm font-medium text-[#09090B] hover:bg-teal-300 transition-colors disabled:opacity-50"
            >
              Start Sync
              <ArrowRight className="w-4 h-4" />
            </button>
          </>
        )}

        {step === 2 && (
          <div className="flex flex-col items-center gap-4 py-8">
            <Loader2 className="w-8 h-8 animate-spin text-teal-400" />
            <p className="text-sm text-[#A1A1AA]">
              Syncing {objects.join(", ")} from HubSpot...
            </p>
          </div>
        )}

        {step === 3 && (
          <div className="space-y-5">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-emerald-500/10 flex items-center justify-center">
                <Check className="w-5 h-5 text-emerald-400" />
              </div>
              <div>
                <p className="text-sm font-semibold text-[#FAFAFA]">
                  Sync Complete
                </p>
                <p className="text-xs text-[#71717A]">
                  Your CRM data is now available as agent memory.
                </p>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              {Object.entries(counts).map(([key, val]) => (
                <div
                  key={key}
                  className="rounded-md border border-[#27272A] bg-[#111114] px-4 py-3"
                >
                  <p className="text-[10px] uppercase tracking-wider text-[#71717A]">
                    {key}
                  </p>
                  <p className="text-lg font-semibold text-[#FAFAFA] font-mono">
                    {val}
                  </p>
                </div>
              ))}
            </div>
            <Link
              href="/dashboard/agents"
              className="inline-flex items-center gap-2 rounded-md bg-[#2DD4BF] px-4 py-2 text-sm font-medium text-[#09090B] hover:bg-teal-300 transition-colors"
            >
              Go to Agents
              <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
