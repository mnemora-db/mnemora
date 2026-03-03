"use client";

import { useState } from "react";
import { MessageSquarePlus, Star, Bug, Lightbulb, Send, Check } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";

type FeedbackType = "bug" | "feature" | "feedback";
type Severity = "critical" | "major" | "minor";
type Status = "idle" | "submitting" | "success" | "error";

export function FeedbackWidget() {
  const [open, setOpen] = useState(false);
  const [tab, setTab] = useState<FeedbackType>("bug");
  const [status, setStatus] = useState<Status>("idle");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Bug form
  const [bugTitle, setBugTitle] = useState("");
  const [bugDesc, setBugDesc] = useState("");
  const [bugSteps, setBugSteps] = useState("");
  const [severity, setSeverity] = useState<Severity>("minor");

  // Feature form
  const [featureTitle, setFeatureTitle] = useState("");
  const [featureDesc, setFeatureDesc] = useState("");
  const [useCase, setUseCase] = useState("");

  // General feedback
  const [feedbackText, setFeedbackText] = useState("");
  const [rating, setRating] = useState(0);

  function resetForms() {
    setBugTitle("");
    setBugDesc("");
    setBugSteps("");
    setSeverity("minor");
    setFeatureTitle("");
    setFeatureDesc("");
    setUseCase("");
    setFeedbackText("");
    setRating(0);
    setErrorMsg(null);
    setStatus("idle");
  }

  function handleOpenChange(next: boolean) {
    setOpen(next);
    if (!next) {
      // Reset after close animation
      setTimeout(resetForms, 200);
    }
  }

  async function handleSubmit() {
    setStatus("submitting");
    setErrorMsg(null);

    let body: Record<string, unknown> = { type: tab };

    if (tab === "bug") {
      if (!bugTitle.trim()) {
        setErrorMsg("Title is required.");
        setStatus("idle");
        return;
      }
      body = {
        ...body,
        title: bugTitle.trim(),
        description: bugDesc.trim(),
        steps_to_reproduce: bugSteps.trim() || null,
        severity,
      };
    } else if (tab === "feature") {
      if (!featureTitle.trim()) {
        setErrorMsg("Title is required.");
        setStatus("idle");
        return;
      }
      body = {
        ...body,
        title: featureTitle.trim(),
        description: featureDesc.trim(),
        use_case: useCase.trim() || null,
      };
    } else {
      if (!feedbackText.trim()) {
        setErrorMsg("Please enter your feedback.");
        setStatus("idle");
        return;
      }
      body = {
        ...body,
        title: "General feedback",
        description: feedbackText.trim(),
        rating: rating > 0 ? rating : null,
      };
    }

    try {
      const res = await fetch("/api/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.error ?? "Failed to submit feedback");
      }

      setStatus("success");
      setTimeout(() => handleOpenChange(false), 1800);
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Something went wrong");
      setStatus("error");
    }
  }

  const isSubmitting = status === "submitting";

  return (
    <>
      {/* Floating trigger button */}
      <button
        onClick={() => setOpen(true)}
        className="fixed bottom-6 right-6 z-40 w-12 h-12 rounded-full bg-[#2DD4BF] text-[#09090B] shadow-lg hover:bg-[#2DD4BF]/90 transition-all duration-150 flex items-center justify-center hover:scale-105 active:scale-95"
        aria-label="Send feedback"
      >
        <MessageSquarePlus className="w-5 h-5" />
      </button>

      <Dialog open={open} onOpenChange={handleOpenChange}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Send Feedback</DialogTitle>
            <DialogDescription>
              Help us improve Mnemora. Your feedback creates a GitHub issue
              automatically.
            </DialogDescription>
          </DialogHeader>

          {/* Success state */}
          {status === "success" ? (
            <div className="flex flex-col items-center gap-3 py-6">
              <div className="w-12 h-12 rounded-full bg-green-500/10 border border-green-500/20 flex items-center justify-center">
                <Check className="w-6 h-6 text-green-500" />
              </div>
              <p className="text-sm font-medium text-[#FAFAFA]">
                Thank you for your feedback!
              </p>
              <p className="text-xs text-[#71717A]">
                A GitHub issue has been created.
              </p>
            </div>
          ) : (
            <Tabs
              value={tab}
              onValueChange={(v) => {
                setTab(v as FeedbackType);
                setErrorMsg(null);
              }}
            >
              <TabsList className="grid w-full grid-cols-3 bg-[#111114]">
                <TabsTrigger
                  value="bug"
                  className="gap-1.5 text-xs data-[state=active]:bg-[#18181B]"
                >
                  <Bug className="w-3.5 h-3.5" aria-hidden="true" />
                  Bug
                </TabsTrigger>
                <TabsTrigger
                  value="feature"
                  className="gap-1.5 text-xs data-[state=active]:bg-[#18181B]"
                >
                  <Lightbulb className="w-3.5 h-3.5" aria-hidden="true" />
                  Feature
                </TabsTrigger>
                <TabsTrigger
                  value="feedback"
                  className="gap-1.5 text-xs data-[state=active]:bg-[#18181B]"
                >
                  <Star className="w-3.5 h-3.5" aria-hidden="true" />
                  Feedback
                </TabsTrigger>
              </TabsList>

              {/* ── Bug Report ── */}
              <TabsContent value="bug" className="space-y-3 mt-4">
                <div className="space-y-1.5">
                  <Label htmlFor="bug-title" className="text-[#A1A1AA]">
                    Title <span className="text-red-400">*</span>
                  </Label>
                  <Input
                    id="bug-title"
                    placeholder="Brief summary of the bug"
                    value={bugTitle}
                    onChange={(e) => setBugTitle(e.target.value)}
                    className="bg-[#111114] border-[#27272A] text-[#FAFAFA] placeholder:text-[#52525B]"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="bug-desc" className="text-[#A1A1AA]">
                    Description
                  </Label>
                  <Textarea
                    id="bug-desc"
                    placeholder="What happened? What did you expect?"
                    rows={3}
                    value={bugDesc}
                    onChange={(e) => setBugDesc(e.target.value)}
                    className="bg-[#111114] border-[#27272A] text-[#FAFAFA] placeholder:text-[#52525B] resize-none"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="bug-steps" className="text-[#A1A1AA]">
                    Steps to Reproduce
                  </Label>
                  <Textarea
                    id="bug-steps"
                    placeholder="1. Go to...&#10;2. Click on...&#10;3. See error"
                    rows={3}
                    value={bugSteps}
                    onChange={(e) => setBugSteps(e.target.value)}
                    className="bg-[#111114] border-[#27272A] text-[#FAFAFA] placeholder:text-[#52525B] resize-none"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label className="text-[#A1A1AA]">Severity</Label>
                  <div className="flex gap-2">
                    {(["minor", "major", "critical"] as const).map((s) => (
                      <button
                        key={s}
                        type="button"
                        onClick={() => setSeverity(s)}
                        className={cn(
                          "px-3 py-1.5 rounded-md text-xs font-medium border transition-colors duration-150 capitalize",
                          severity === s
                            ? s === "critical"
                              ? "border-red-500/50 bg-red-500/10 text-red-400"
                              : s === "major"
                                ? "border-amber-500/50 bg-amber-500/10 text-amber-400"
                                : "border-[#3F3F46] bg-[#111114] text-[#FAFAFA]"
                            : "border-[#27272A] bg-transparent text-[#71717A] hover:border-[#3F3F46] hover:text-[#A1A1AA]"
                        )}
                      >
                        {s}
                      </button>
                    ))}
                  </div>
                </div>
              </TabsContent>

              {/* ── Feature Request ── */}
              <TabsContent value="feature" className="space-y-3 mt-4">
                <div className="space-y-1.5">
                  <Label htmlFor="feat-title" className="text-[#A1A1AA]">
                    Title <span className="text-red-400">*</span>
                  </Label>
                  <Input
                    id="feat-title"
                    placeholder="Feature name"
                    value={featureTitle}
                    onChange={(e) => setFeatureTitle(e.target.value)}
                    className="bg-[#111114] border-[#27272A] text-[#FAFAFA] placeholder:text-[#52525B]"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="feat-desc" className="text-[#A1A1AA]">
                    Description
                  </Label>
                  <Textarea
                    id="feat-desc"
                    placeholder="Describe the feature you'd like to see"
                    rows={3}
                    value={featureDesc}
                    onChange={(e) => setFeatureDesc(e.target.value)}
                    className="bg-[#111114] border-[#27272A] text-[#FAFAFA] placeholder:text-[#52525B] resize-none"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="feat-usecase" className="text-[#A1A1AA]">
                    Use Case
                  </Label>
                  <Textarea
                    id="feat-usecase"
                    placeholder="How would you use this feature?"
                    rows={3}
                    value={useCase}
                    onChange={(e) => setUseCase(e.target.value)}
                    className="bg-[#111114] border-[#27272A] text-[#FAFAFA] placeholder:text-[#52525B] resize-none"
                  />
                </div>
              </TabsContent>

              {/* ── General Feedback ── */}
              <TabsContent value="feedback" className="space-y-3 mt-4">
                <div className="space-y-1.5">
                  <Label className="text-[#A1A1AA]">
                    How would you rate Mnemora?
                  </Label>
                  <div className="flex gap-1">
                    {[1, 2, 3, 4, 5].map((n) => (
                      <button
                        key={n}
                        type="button"
                        onClick={() => setRating(n)}
                        aria-label={`Rate ${n} star${n > 1 ? "s" : ""}`}
                        className="p-1 transition-colors duration-100"
                      >
                        <Star
                          className={cn(
                            "w-6 h-6 transition-colors duration-100",
                            n <= rating
                              ? "fill-amber-400 text-amber-400"
                              : "text-[#3F3F46] hover:text-[#52525B]"
                          )}
                        />
                      </button>
                    ))}
                  </div>
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="gen-feedback" className="text-[#A1A1AA]">
                    Your Feedback <span className="text-red-400">*</span>
                  </Label>
                  <Textarea
                    id="gen-feedback"
                    placeholder="Tell us what you think..."
                    rows={5}
                    value={feedbackText}
                    onChange={(e) => setFeedbackText(e.target.value)}
                    className="bg-[#111114] border-[#27272A] text-[#FAFAFA] placeholder:text-[#52525B] resize-none"
                  />
                </div>
              </TabsContent>

              {/* Error message */}
              {errorMsg && (
                <p className="text-xs text-red-400 mt-1">{errorMsg}</p>
              )}

              {/* Submit button */}
              <button
                onClick={handleSubmit}
                disabled={isSubmitting}
                className="mt-2 w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-md bg-[#2DD4BF] text-[#09090B] text-sm font-semibold hover:bg-[#2DD4BF]/90 transition-colors duration-150 disabled:opacity-50"
              >
                <Send className="w-3.5 h-3.5" aria-hidden="true" />
                {isSubmitting ? "Submitting..." : "Submit"}
              </button>
            </Tabs>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}
