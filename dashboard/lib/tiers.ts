/**
 * Shared tier definitions for Mnemora pricing plans.
 *
 * Used by: billing page, sidebar, usage page, webhook handler.
 */

export interface TierLimits {
  label: string;
  price: number; // -1 = "Contact us"
  apiCallsPerDay: string;
  storage: string;
  vectors: string;
  agents: string;
  support: string;
}

export const TIER_LIMITS: Record<string, TierLimits> = {
  free: {
    label: "Free",
    price: 0,
    apiCallsPerDay: "500",
    storage: "50 MB",
    vectors: "5K",
    agents: "1",
    support: "Community",
  },
  starter: {
    label: "Starter",
    price: 29,
    apiCallsPerDay: "5,000",
    storage: "500 MB",
    vectors: "50K",
    agents: "10",
    support: "Email",
  },
  pro: {
    label: "Pro",
    price: 49,
    apiCallsPerDay: "25,000",
    storage: "5 GB",
    vectors: "250K",
    agents: "50",
    support: "Priority",
  },
  scale: {
    label: "Scale",
    price: 99,
    apiCallsPerDay: "50,000",
    storage: "10 GB",
    vectors: "500K",
    agents: "Unlimited",
    support: "Dedicated",
  },
  enterprise: {
    label: "Enterprise",
    price: -1,
    apiCallsPerDay: "Unlimited",
    storage: "Unlimited",
    vectors: "Unlimited",
    agents: "Unlimited",
    support: "Custom SLA",
  },
};

export const TIER_ORDER = ["free", "starter", "pro", "scale", "enterprise"] as const;

export type TierName = (typeof TIER_ORDER)[number];

export const VALID_TIERS: string[] = [...TIER_ORDER];

export const CREALA_LINKS: Record<string, string> = {
  starter: "https://pay.crea.la/b/dRm9AS5XV89869yfPM1VN3S",
  pro: "https://pay.crea.la/b/fZu4gygCz9dc9lKgTQ1VN3U",
  scale: "https://pay.crea.la/b/4gMdR8fyvgFEcxW4741VN3V",
};

/** Badge color classes for each tier. */
export const TIER_BADGE_COLORS: Record<string, string> = {
  free: "bg-[#27272A]/50 text-[#A1A1AA] border-[#3F3F46]",
  starter: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  pro: "bg-[#2DD4BF]/10 text-[#2DD4BF] border-[#2DD4BF]/20",
  scale: "bg-purple-500/10 text-purple-400 border-purple-500/20",
  enterprise: "bg-amber-500/10 text-amber-400 border-amber-500/20",
};
