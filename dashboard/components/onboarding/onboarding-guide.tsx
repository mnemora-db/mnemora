"use client";

import { useState, useEffect } from "react";
import { ArrowRight, Copy, Check, X, KeyRound, Terminal, Code2 } from "lucide-react";
import Link from "next/link";

const STORAGE_KEY = "mnemora-onboarding-dismissed";

const CODE_SNIPPET = `from mnemora import Mnemora

m = Mnemora(api_key="mnm_...")
m.state.put("agent-1", {"mood": "curious"})
print(m.state.get("agent-1"))`;

interface Step {
  title: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
}

const STEPS: Step[] = [
  {
    title: "Create your API key",
    description: "Head to API Keys and generate your first key. You'll need it to authenticate SDK calls.",
    icon: KeyRound,
  },
  {
    title: "Install the SDK",
    description: "Install the Mnemora Python SDK from PyPI.",
    icon: Terminal,
  },
  {
    title: "Store your first memory",
    description: "Use the SDK to store and retrieve agent state in under 10ms.",
    icon: Code2,
  },
];

export function OnboardingGuide() {
  const [dismissed, setDismissed] = useState(true); // default hidden
  const [hasKey, setHasKey] = useState(true); // default hidden
  const [step, setStep] = useState(0);
  const [copiedPip, setCopiedPip] = useState(false);
  const [copiedCode, setCopiedCode] = useState(false);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    // Check localStorage
    const wasDismissed = localStorage.getItem(STORAGE_KEY) === "true";
    setDismissed(wasDismissed);

    // Check if user has an API key
    fetch("/api/keys")
      .then((r) => r.json())
      .then((data) => {
        setHasKey(data.has_key === true);
        setLoaded(true);
      })
      .catch(() => {
        setLoaded(true);
      });
  }, []);

  function handleDismiss() {
    setDismissed(true);
    localStorage.setItem(STORAGE_KEY, "true");
  }

  async function handleCopy(text: string, type: "pip" | "code") {
    try {
      await navigator.clipboard.writeText(text);
      if (type === "pip") {
        setCopiedPip(true);
        setTimeout(() => setCopiedPip(false), 2000);
      } else {
        setCopiedCode(true);
        setTimeout(() => setCopiedCode(false), 2000);
      }
    } catch {
      // Clipboard API unavailable
    }
  }

  // Don't show if: loading, dismissed, or user already has a key
  if (!loaded || dismissed || hasKey) return null;

  const currentStep = STEPS[step];
  const StepIcon = currentStep.icon;

  return (
    <div className="mb-6 rounded-xl border border-[#2DD4BF]/20 bg-gradient-to-br from-[#2DD4BF]/[0.04] to-transparent p-5 relative">
      {/* Dismiss button */}
      <button
        onClick={handleDismiss}
        className="absolute top-3 right-3 w-7 h-7 flex items-center justify-center rounded-md text-[#71717A] hover:text-[#FAFAFA] hover:bg-[#18181B] transition-colors duration-150"
        aria-label="Dismiss onboarding"
      >
        <X className="w-4 h-4" />
      </button>

      {/* Header */}
      <div className="flex items-center gap-3 mb-4">
        <div className="w-8 h-8 rounded-lg bg-[#2DD4BF]/10 border border-[#2DD4BF]/20 flex items-center justify-center">
          <StepIcon className="w-4 h-4 text-[#2DD4BF]" />
        </div>
        <div>
          <p className="text-xs text-[#71717A] font-medium">
            Getting started &middot; Step {step + 1} of {STEPS.length}
          </p>
          <h3 className="text-sm font-semibold text-[#FAFAFA]">
            {currentStep.title}
          </h3>
        </div>
      </div>

      {/* Step content */}
      <p className="text-xs text-[#A1A1AA] mb-4 max-w-lg">
        {currentStep.description}
      </p>

      {/* Step-specific content */}
      {step === 0 && (
        <Link
          href="/dashboard/api-keys"
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-[#2DD4BF] text-[#09090B] text-xs font-semibold hover:bg-[#2DD4BF]/90 transition-colors duration-150"
        >
          Go to API Keys
          <ArrowRight className="w-3 h-3" />
        </Link>
      )}

      {step === 1 && (
        <div className="flex items-center gap-2">
          <code className="flex-1 font-mono text-xs text-[#2DD4BF] bg-[#111114] border border-[#27272A] rounded-md px-3 py-2">
            pip install mnemora-sdk
          </code>
          <button
            onClick={() => handleCopy("pip install mnemora-sdk", "pip")}
            className="w-8 h-8 flex items-center justify-center rounded-md border border-[#27272A] bg-[#111114] text-[#71717A] hover:text-[#FAFAFA] hover:border-[#3F3F46] transition-colors duration-150 shrink-0"
            aria-label={copiedPip ? "Copied" : "Copy command"}
          >
            {copiedPip ? (
              <Check className="w-3.5 h-3.5 text-green-500" />
            ) : (
              <Copy className="w-3.5 h-3.5" />
            )}
          </button>
        </div>
      )}

      {step === 2 && (
        <div className="relative">
          <pre className="font-mono text-xs text-[#A1A1AA] bg-[#111114] border border-[#27272A] rounded-md px-3 py-3 overflow-x-auto">
            {CODE_SNIPPET}
          </pre>
          <button
            onClick={() => handleCopy(CODE_SNIPPET, "code")}
            className="absolute top-2 right-2 w-7 h-7 flex items-center justify-center rounded-md border border-[#27272A] bg-[#111114] text-[#71717A] hover:text-[#FAFAFA] hover:border-[#3F3F46] transition-colors duration-150"
            aria-label={copiedCode ? "Copied" : "Copy code"}
          >
            {copiedCode ? (
              <Check className="w-3 h-3 text-green-500" />
            ) : (
              <Copy className="w-3 h-3" />
            )}
          </button>
        </div>
      )}

      {/* Step indicator + navigation */}
      <div className="flex items-center justify-between mt-4 pt-3 border-t border-[#27272A]/50">
        {/* Step dots */}
        <div className="flex items-center gap-1.5">
          {STEPS.map((_, i) => (
            <div
              key={i}
              className={`w-1.5 h-1.5 rounded-full transition-colors duration-150 ${
                i === step
                  ? "bg-[#2DD4BF]"
                  : i < step
                    ? "bg-[#2DD4BF]/40"
                    : "bg-[#27272A]"
              }`}
            />
          ))}
        </div>

        {/* Buttons */}
        <div className="flex items-center gap-2">
          <button
            onClick={handleDismiss}
            className="px-3 py-1 rounded-md text-xs text-[#71717A] hover:text-[#A1A1AA] transition-colors duration-150"
          >
            Skip
          </button>
          {step < STEPS.length - 1 ? (
            <button
              onClick={() => setStep(step + 1)}
              className="flex items-center gap-1 px-3 py-1 rounded-md text-xs font-medium text-[#2DD4BF] hover:bg-[#2DD4BF]/10 transition-colors duration-150"
            >
              Next
              <ArrowRight className="w-3 h-3" />
            </button>
          ) : (
            <button
              onClick={handleDismiss}
              className="flex items-center gap-1 px-3 py-1.5 rounded-md text-xs font-semibold bg-[#2DD4BF] text-[#09090B] hover:bg-[#2DD4BF]/90 transition-colors duration-150"
            >
              Done
              <Check className="w-3 h-3" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
