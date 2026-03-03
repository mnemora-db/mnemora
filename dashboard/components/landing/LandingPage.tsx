"use client";

import { useState } from "react";
import Link from "next/link";
import {
  Github,
  ChevronDown,
  Check,
  X,
  ArrowRight,
  Database,
  Brain,
  Clock,
  Zap,
  Code2,
  Layers,
  Server,
  Users,
  Activity,
  BookOpen,
  ExternalLink,
} from "lucide-react";
import { HeroCtaButton } from "@/components/auth/hero-cta-button";

// ─── Design tokens ─────────────────────────────────────────────────────────────
// bg: #09090B | surface: #111114 | card: #18181B | border: #27272A
// text: #FAFAFA | muted: #A1A1AA | subtle: #71717A | dim: #52525B
// accent: #2DD4BF

// ─── Logo ──────────────────────────────────────────────────────────────────────
function MnemoraLogo({ size = 20 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 20 20"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <path
        d="M3 16V4L10 11L17 4V16"
        stroke="#2DD4BF"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

// ─── Data ──────────────────────────────────────────────────────────────────────
type CellValue = string | boolean;

interface ComparisonRow {
  feature: string;
  mnemora: CellValue;
  mem0: CellValue;
  zep: CellValue;
  letta: CellValue;
}

const COMPARISON_FEATURES: ComparisonRow[] = [
  {
    feature: "Memory types",
    mnemora: "4 (state, semantic, episodic, procedural)",
    mem0: "1 (semantic only)",
    zep: "2 (semantic + temporal)",
    letta: "2 (core + archival)",
  },
  {
    feature: "Vector search",
    mnemora: "pgvector 1024d",
    mem0: "External DB",
    zep: "Built-in",
    letta: "Built-in",
  },
  {
    feature: "LLM required for CRUD",
    mnemora: false,
    mem0: "Every op",
    zep: false,
    letta: "Every op",
  },
  {
    feature: "Serverless",
    mnemora: true,
    mem0: false,
    zep: false,
    letta: false,
  },
  {
    feature: "Self-hostable",
    mnemora: true,
    mem0: false,
    zep: "Partial",
    letta: true,
  },
  {
    feature: "Multi-tenant",
    mnemora: true,
    mem0: false,
    zep: true,
    letta: false,
  },
  {
    feature: "LangGraph checkpoints",
    mnemora: true,
    mem0: false,
    zep: false,
    letta: false,
  },
  {
    feature: "State latency",
    mnemora: "<10ms",
    mem0: "~500ms",
    zep: "<200ms",
    letta: "~1s",
  },
];

const FAQS = [
  {
    q: "What exactly is Mnemora?",
    a: "Mnemora is a serverless memory infrastructure for AI agents. It provides four types of memory — working (key-value state), semantic (vector similarity search), episodic (time-series event log), and procedural (tool definitions and rules) — all behind a single REST API and Python SDK.",
  },
  {
    q: "How is Mnemora different from Mem0 or Zep?",
    a: "The core difference is architecture. Mem0 and Letta require an LLM call for every memory operation, adding latency and cost. Mnemora does direct CRUD with sub-10ms state reads. We also support 4 memory types (vs 1-2 for competitors), are truly serverless (scales to zero), and natively support LangGraph checkpoints.",
  },
  {
    q: "Is it really serverless?",
    a: "Yes. Mnemora is built entirely on AWS serverless services: DynamoDB on-demand, Aurora Serverless v2 (scales to zero), Lambda ARM64, and S3 for cold storage. You pay per request with no idle compute costs. The managed cloud is provisioned by us; self-hosters deploy via CDK.",
  },
  {
    q: "How does semantic memory work?",
    a: "When you call store_memory(), the text is automatically embedded server-side using Amazon Bedrock Titan (1024 dimensions). The vector is stored in Aurora pgvector. Duplicate content (cosine similarity > 0.95) is merged rather than re-inserted. Similarity search returns the top-k most relevant memories for any query.",
  },
  {
    q: "Can I self-host Mnemora?",
    a: "Yes. The infrastructure code deploys to your AWS account with npx cdk deploy. This provisions DynamoDB, Aurora Serverless v2 with pgvector, Lambda, API Gateway, S3, and CloudWatch dashboards. Estimated idle cost is ~$15/month. Aurora scales to zero when not in use.",
  },
  {
    q: "What frameworks are supported?",
    a: "Mnemora has native integrations for LangGraph (as a CheckpointSaver), LangChain (as BaseChatMessageHistory), and CrewAI (as a Storage backend). The REST API is framework-agnostic, so any agent framework can use it via HTTP.",
  },
  {
    q: "How does multi-tenancy work?",
    a: "Each API key is scoped to a tenant. Within a tenant, each agent gets its own isolated memory namespace identified by agent_id. Cross-agent search is not possible, and data is never mixed between tenants at the database layer.",
  },
  {
    q: "Is data encrypted?",
    a: "All data at rest is encrypted by AWS (AES-256 for DynamoDB and S3, Postgres TDE for Aurora). All data in transit uses TLS. API keys are hashed before storage and never returned in plaintext after creation.",
  },
];

const PRICING_TIERS = [
  {
    name: "Free",
    price: 0,
    description: "For exploration and side projects",
    href: "/dashboard",
    features: [
      "10,000 ops / month",
      "1 agent",
      "500 MB storage",
      "Community support",
      "Working + semantic memory",
    ],
    cta: "Get started",
    highlight: false,
  },
  {
    name: "Starter",
    price: 19,
    description: "For early-stage products",
    href: "https://app.crea.la/mnemora/starter",
    features: [
      "100,000 ops / month",
      "10 agents",
      "5 GB storage",
      "Email support",
      "All memory types",
      "API analytics",
    ],
    cta: "Subscribe",
    highlight: false,
  },
  {
    name: "Pro",
    price: 79,
    description: "For production applications",
    href: "https://app.crea.la/mnemora/pro",
    features: [
      "1M ops / month",
      "Unlimited agents",
      "50 GB storage",
      "Priority support",
      "All memory types",
      "Advanced analytics",
      "LangGraph checkpoints",
    ],
    cta: "Subscribe",
    highlight: true,
  },
  {
    name: "Scale",
    price: 299,
    description: "For high-volume teams",
    href: "https://app.crea.la/mnemora/scale",
    features: [
      "10M ops / month",
      "Unlimited agents",
      "500 GB storage",
      "Dedicated support + SLA",
      "All memory types",
      "Custom integrations",
      "Invoice billing",
    ],
    cta: "Subscribe",
    highlight: false,
  },
];

const BLOG_POSTS = [
  {
    title: "Understanding Agent Memory: A Developer's Guide",
    description:
      "A deep dive into the four types of memory AI agents need and why each matters for building production-grade systems.",
    tag: "Guide",
    readTime: "8 min",
  },
  {
    title: "Building Persistent AI Agents with LangGraph and Mnemora",
    description:
      "Step-by-step tutorial: how to use MnemoraCheckpointSaver to give your LangGraph agents durable, cross-session memory.",
    tag: "Tutorial",
    readTime: "12 min",
  },
  {
    title: "Why Serverless Memory Matters for AI at Scale",
    description:
      "The economics of serverless infrastructure for AI workloads — and why stateless-by-default is the wrong architecture choice.",
    tag: "Architecture",
    readTime: "6 min",
  },
];

// ─── Helpers ───────────────────────────────────────────────────────────────────
function CellIcon({ value }: { value: CellValue }) {
  if (value === true)
    return <Check className="w-4 h-4 text-[#2DD4BF] mx-auto" />;
  if (value === false)
    return <X className="w-4 h-4 text-[#52525B] mx-auto" />;
  const str = String(value);
  if (str.toLowerCase() === "partial")
    return (
      <span className="text-[#A1A1AA] text-xs inline-block text-center">
        Partial
      </span>
    );
  return (
    <span className="text-[#A1A1AA] text-xs inline-block text-center">
      {str}
    </span>
  );
}

// ─── Navbar ────────────────────────────────────────────────────────────────────
function Navbar() {
  return (
    <header className="sticky top-0 z-50 w-full border-b border-[#27272A]/80 bg-[#09090B]/90 backdrop-blur-md">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
        {/* Logo */}
        <Link
          href="/"
          className="flex items-center gap-2.5 text-[#FAFAFA] font-semibold tracking-tight"
        >
          <div className="w-7 h-7 rounded flex items-center justify-center bg-[#18181B] border border-[#27272A]">
            <MnemoraLogo size={16} />
          </div>
          <span>mnemora</span>
        </Link>

        {/* Nav links */}
        <nav className="hidden md:flex items-center gap-6 text-sm text-[#71717A]">
          <a href="#features" className="hover:text-[#FAFAFA] transition-colors duration-150">Features</a>
          <a href="#compare" className="hover:text-[#FAFAFA] transition-colors duration-150">Compare</a>
          <a href="#pricing" className="hover:text-[#FAFAFA] transition-colors duration-150">Pricing</a>
          <a href="#blog" className="hover:text-[#FAFAFA] transition-colors duration-150">Blog</a>
          <a href="#faq" className="hover:text-[#FAFAFA] transition-colors duration-150">FAQ</a>
        </nav>

        {/* Actions */}
        <div className="flex items-center gap-3">
          <a
            href="https://github.com/mnemora-db/mnemora"
            target="_blank"
            rel="noopener noreferrer"
            className="hidden sm:flex items-center justify-center w-8 h-8 rounded-md text-[#71717A] hover:text-[#FAFAFA] hover:bg-[#18181B] transition-all duration-150"
            aria-label="GitHub"
          >
            <Github className="w-4 h-4" />
          </a>
          <Link
            href="/dashboard"
            className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-md bg-[#2DD4BF] text-[#09090B] text-sm font-semibold hover:bg-[#2DD4BF]/90 transition-colors duration-150"
          >
            Get started
          </Link>
        </div>
      </div>
    </header>
  );
}

// ─── Hero ──────────────────────────────────────────────────────────────────────
function HeroSection() {
  return (
    <section className="relative overflow-hidden pt-24 pb-20 px-4 text-center">
      {/* Aurora gradient blobs */}
      <div
        className="absolute pointer-events-none"
        style={{
          top: "-10%",
          left: "15%",
          width: "600px",
          height: "600px",
          borderRadius: "50%",
          background: "radial-gradient(circle, rgba(45,212,191,0.07) 0%, transparent 70%)",
          animation: "aurora1 12s ease-in-out infinite",
        }}
      />
      <div
        className="absolute pointer-events-none"
        style={{
          top: "5%",
          right: "10%",
          width: "500px",
          height: "500px",
          borderRadius: "50%",
          background: "radial-gradient(circle, rgba(167,139,250,0.05) 0%, transparent 70%)",
          animation: "aurora2 15s ease-in-out infinite",
        }}
      />
      <div
        className="absolute pointer-events-none"
        style={{
          top: "20%",
          left: "40%",
          width: "400px",
          height: "400px",
          borderRadius: "50%",
          background: "radial-gradient(circle, rgba(56,189,248,0.04) 0%, transparent 70%)",
          animation: "aurora3 18s ease-in-out infinite",
        }}
      />
      {/* Teal glow */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background:
            "radial-gradient(ellipse 80% 50% at 50% 0%, rgba(45,212,191,0.10) 0%, transparent 70%)",
        }}
      />
      {/* Dot grid pattern */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          backgroundImage:
            "radial-gradient(circle, rgba(250,250,250,0.04) 1px, transparent 1px)",
          backgroundSize: "24px 24px",
        }}
      />

      <div className="relative max-w-4xl mx-auto">
        {/* Badge */}
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-[#2DD4BF]/30 bg-[#2DD4BF]/[0.08] text-[#2DD4BF] text-xs font-medium mb-8">
          <span className="w-1.5 h-1.5 rounded-full bg-[#2DD4BF] animate-pulse" />
          Open Source · Serverless · AWS-native
        </div>

        {/* Headline */}
        <h1 className="text-4xl sm:text-5xl md:text-[64px] font-bold text-[#FAFAFA] tracking-tight leading-[1.08] mb-6">
          The memory infrastructure
          <br className="hidden sm:block" />
          <span
            className="text-transparent bg-clip-text"
            style={{
              backgroundImage: "linear-gradient(90deg, #2DD4BF 0%, #38BDF8 100%)",
            }}
          >
            {" "}for AI agents
          </span>
        </h1>

        <p className="text-base sm:text-lg text-[#A1A1AA] max-w-2xl mx-auto mb-10 leading-relaxed">
          One API for four memory types. Working, semantic, episodic, and
          procedural — all serverless, all AWS-native. Give your agents
          persistent memory in minutes, not months.
        </p>

        {/* CTAs */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-3 mb-14">
          <HeroCtaButton />
          <a
            href="https://github.com/mnemora-db/mnemora"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 px-6 py-3 rounded-lg border border-[#27272A] text-[#A1A1AA] text-sm font-medium hover:border-[#3F3F46] hover:text-[#FAFAFA] transition-all duration-150"
          >
            <Github className="w-4 h-4" />
            View on GitHub
          </a>
        </div>

        {/* Architecture pills */}
        <div className="flex flex-wrap items-center justify-center gap-2 text-xs">
          {[
            { label: "DynamoDB", color: "#F59E0B" },
            { label: "pgvector", color: "#2DD4BF" },
            { label: "S3", color: "#38BDF8" },
            { label: "Bedrock Titan", color: "#A78BFA" },
          ].map(({ label, color }, i) => (
            <span key={label} className="flex items-center gap-2">
              <span
                className="flex items-center gap-1.5 px-2.5 py-1 rounded border border-[#27272A] bg-[#111114] text-[#71717A]"
              >
                <span
                  className="w-1.5 h-1.5 rounded-full"
                  style={{ backgroundColor: color }}
                />
                {label}
              </span>
              {i < 3 && (
                <span className="text-[#27272A] hidden sm:inline">·</span>
              )}
            </span>
          ))}
        </div>
      </div>
    </section>
  );
}

// ─── Trust strip ───────────────────────────────────────────────────────────────
function TrustStrip() {
  const frameworks = ["LangGraph", "LangChain", "CrewAI", "AutoGen", "OpenAI Agents SDK"];
  return (
    <section className="border-y border-[#27272A]/50 bg-[#111114]/40 py-5">
      <div className="max-w-4xl mx-auto px-4 flex flex-wrap items-center justify-center gap-x-8 gap-y-2">
        <span className="text-xs text-[#3F3F46]">Works with</span>
        {frameworks.map((fw) => (
          <span key={fw} className="text-xs text-[#71717A] font-medium">
            {fw}
          </span>
        ))}
      </div>
    </section>
  );
}

// ─── Problem ───────────────────────────────────────────────────────────────────
function ProblemSection() {
  const problems = [
    {
      icon: Database,
      title: "Four databases to stitch together",
      body: "Redis for state. Pinecone for vectors. Postgres for structured data. S3 for logs. Four billing accounts, four clients, zero unified memory layer.",
    },
    {
      icon: Layers,
      title: "No unified query layer",
      body: "State lives here. Vectors live there. Events are somewhere else. You write glue code instead of writing agents.",
    },
    {
      icon: Zap,
      title: "Agents forget everything",
      body: "Without persistence, every invocation starts from scratch. Context, preferences, and history vanish between calls.",
    },
  ];

  return (
    <section className="py-20 px-4">
      <div className="max-w-5xl mx-auto">
        <div className="text-center mb-12">
          <span className="text-xs font-semibold text-[#52525B] uppercase tracking-widest">
            The problem
          </span>
          <h2 className="text-2xl sm:text-3xl font-bold text-[#FAFAFA] mt-3 tracking-tight">
            AI agents are stateless by default
          </h2>
          <p className="text-[#71717A] text-sm mt-3 max-w-lg mx-auto">
            To give them memory, developers stitch together four databases,
            four clients, four billing accounts — with no unified query layer.
          </p>
        </div>

        <div className="grid sm:grid-cols-3 gap-4">
          {problems.map(({ icon: Icon, title, body }) => (
            <div
              key={title}
              className="group relative rounded-xl p-px bg-gradient-to-b from-[#2DD4BF]/10 via-[#27272A] to-[#A78BFA]/10 transition-all duration-300 hover:-translate-y-0.5 hover:shadow-[0_0_30px_rgba(45,212,191,0.08)]"
            >
              <div className="rounded-[11px] bg-[#111114]/80 backdrop-blur-sm p-6 h-full">
                <div className="w-9 h-9 rounded-lg bg-[#18181B] border border-[#27272A] flex items-center justify-center mb-4">
                  <Icon className="w-4 h-4 text-[#71717A]" />
                </div>
                <h3 className="text-sm font-semibold text-[#FAFAFA] mb-2">
                  {title}
                </h3>
                <p className="text-xs text-[#71717A] leading-relaxed">{body}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

// ─── Solution ──────────────────────────────────────────────────────────────────
function SolutionSection() {
  const types = [
    {
      icon: Zap,
      name: "Working Memory",
      badge: "<10ms",
      badgeColor: "#2DD4BF",
      desc: "Key-value state in DynamoDB. Sub-10ms reads with optimistic locking and configurable TTL. Ideal for agent step state and task context.",
      soon: false,
    },
    {
      icon: Brain,
      name: "Semantic Memory",
      badge: "1024d",
      badgeColor: "#38BDF8",
      desc: "Natural-language text stored as 1024-dimensional vectors in Aurora pgvector. Auto-embedded via Bedrock Titan. Duplicates are merged, not re-inserted.",
      soon: false,
    },
    {
      icon: Clock,
      name: "Episodic Memory",
      badge: "Hot + Cold",
      badgeColor: "#A78BFA",
      desc: "Append-only time-series event log. Hot data in DynamoDB, automatically tiered to S3. Full session replay and time-range queries.",
      soon: false,
    },
    {
      icon: Code2,
      name: "Procedural Memory",
      badge: "v0.2",
      badgeColor: "#71717A",
      desc: "Tool definitions, prompt templates, schemas, and rules stored in Postgres. Version-controlled and queryable by name. Schema is live; SDK methods ship in v0.2.",
      soon: true,
    },
  ];

  return (
    <section id="features" className="py-20 px-4 bg-[#111114]/30">
      <div className="max-w-5xl mx-auto">
        <div className="text-center mb-12">
          <span className="text-xs font-semibold text-[#52525B] uppercase tracking-widest">
            The solution
          </span>
          <h2 className="text-2xl sm:text-3xl font-bold text-[#FAFAFA] mt-3 tracking-tight">
            One API. Four memory types.
          </h2>
          <p className="text-[#71717A] text-sm mt-3 max-w-lg mx-auto">
            AWS-native serverless infrastructure. No LLM required for CRUD
            operations.
          </p>
        </div>

        <div className="grid sm:grid-cols-2 gap-4">
          {types.map(({ icon: Icon, name, badge, badgeColor, desc, soon }) => (
            <div
              key={name}
              className={`group relative rounded-xl p-px transition-all duration-300 ${
                soon
                  ? "bg-[#27272A]/50 opacity-60"
                  : "bg-gradient-to-b from-[#2DD4BF]/10 via-[#27272A] to-[#A78BFA]/10 hover:-translate-y-0.5 hover:shadow-[0_0_30px_rgba(45,212,191,0.08)]"
              }`}
            >
              <div className={`rounded-[11px] p-6 h-full ${soon ? "bg-[#111114]" : "bg-[#111114]/80 backdrop-blur-sm"}`}>
                <div className="flex items-start justify-between mb-4">
                  <div className="w-9 h-9 rounded-lg bg-[#18181B] border border-[#27272A] flex items-center justify-center">
                    <Icon className="w-4 h-4" style={{ color: badgeColor }} />
                  </div>
                  <span
                    className="text-[10px] font-semibold px-2 py-0.5 rounded-full border"
                    style={{
                      color: badgeColor,
                      borderColor: `${badgeColor}40`,
                      backgroundColor: `${badgeColor}12`,
                    }}
                  >
                    {badge}
                  </span>
                </div>
                <h3 className="text-sm font-semibold text-[#FAFAFA] mb-2">
                  {name}
                </h3>
                <p className="text-xs text-[#71717A] leading-relaxed">{desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

// ─── Code example ──────────────────────────────────────────────────────────────
type TokenType = "kw" | "fn" | "str" | "cmt" | "num" | "def";

interface Token {
  t: string;
  c: TokenType;
}

interface CodeLine {
  tokens: Token[];
}

const CODE_LINES: CodeLine[] = [
  { tokens: [{ t: "from", c: "kw" }, { t: " mnemora ", c: "def" }, { t: "import", c: "kw" }, { t: " MnemoraSync", c: "fn" }] },
  { tokens: [] },
  { tokens: [{ t: "with", c: "kw" }, { t: " MnemoraSync(api_key=", c: "def" }, { t: '"mnm_..."', c: "str" }, { t: ") ", c: "def" }, { t: "as", c: "kw" }, { t: " client:", c: "def" }] },
  { tokens: [{ t: "    # Store working-memory state", c: "cmt" }] },
  { tokens: [{ t: "    client.", c: "def" }, { t: "store_state", c: "fn" }, { t: '("agent-1", {', c: "def" }, { t: '"task"', c: "str" }, { t: ": ", c: "def" }, { t: '"summarize Q4"', c: "str" }, { t: ", ", c: "def" }, { t: '"step"', c: "str" }, { t: ": ", c: "def" }, { t: "1", c: "num" }, { t: "})", c: "def" }] },
  { tokens: [] },
  { tokens: [{ t: "    # Semantic memory — auto-embedded server-side", c: "cmt" }] },
  { tokens: [{ t: "    client.", c: "def" }, { t: "store_memory", c: "fn" }, { t: '("agent-1", ', c: "def" }, { t: '"User prefers bullet points over prose."', c: "str" }, { t: ")", c: "def" }] },
  { tokens: [] },
  { tokens: [{ t: "    # Vector search across all stored memories", c: "cmt" }] },
  { tokens: [{ t: "    results = client.", c: "def" }, { t: "search_memory", c: "fn" }, { t: "(", c: "def" }, { t: '"user formatting preferences"', c: "str" }, { t: ', agent_id=', c: "def" }, { t: '"agent-1"', c: "str" }, { t: ")", c: "def" }] },
  { tokens: [{ t: "    ", c: "def" }, { t: "for", c: "kw" }, { t: " r ", c: "def" }, { t: "in", c: "kw" }, { t: " results:", c: "def" }] },
  { tokens: [{ t: "        print", c: "fn" }, { t: "(r.content, r.similarity_score)", c: "def" }] },
  { tokens: [] },
  { tokens: [{ t: "    # Log an episode to the time-series history", c: "cmt" }] },
  { tokens: [{ t: "    client.", c: "def" }, { t: "store_episode", c: "fn" }, { t: '(agent_id=', c: "def" }, { t: '"agent-1"', c: "str" }, { t: ", session_id=", c: "def" }, { t: '"sess-001"', c: "str" }, { t: ",", c: "def" }] },
  { tokens: [{ t: "        type=", c: "def" }, { t: '"action"', c: "str" }, { t: ", content={", c: "def" }, { t: '"tool"', c: "str" }, { t: ": ", c: "def" }, { t: '"summarize"', c: "str" }, { t: ", ", c: "def" }, { t: '"input"', c: "str" }, { t: ": ", c: "def" }, { t: '"Q4 report"', c: "str" }, { t: "})", c: "def" }] },
];

const TOKEN_COLOR: Record<TokenType, string> = {
  kw: "#C084FC",
  fn: "#2DD4BF",
  str: "#86EFAC",
  cmt: "#52525B",
  num: "#FCA5A5",
  def: "#E2E8F0",
};

function CodeSection() {
  return (
    <section className="relative py-20 px-4 overflow-hidden">
      {/* Subtle gradient background */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background:
            "radial-gradient(ellipse 80% 60% at 50% 50%, rgba(167,139,250,0.04) 0%, transparent 50%), radial-gradient(ellipse 60% 40% at 50% 60%, rgba(45,212,191,0.03) 0%, transparent 50%)",
        }}
      />
      <div className="relative max-w-4xl mx-auto">
        <div className="text-center mb-12">
          <span className="text-xs font-semibold text-[#52525B] uppercase tracking-widest">
            Quickstart
          </span>
          <h2 className="text-2xl sm:text-3xl font-bold text-[#FAFAFA] mt-3 tracking-tight">
            Your first agent memory in 15 lines
          </h2>
          <p className="text-[#71717A] text-sm mt-3">
            Install{" "}
            <code className="font-mono text-[#2DD4BF] bg-[#2DD4BF]/8 px-1.5 py-0.5 rounded text-xs">
              pip install mnemora-sdk
            </code>{" "}
            and you&apos;re ready.
          </p>
        </div>

        {/* Code window */}
        <div
          className="rounded-xl border border-[#27272A] bg-[#0D0D10] overflow-hidden"
          style={{ boxShadow: "0 0 60px rgba(45,212,191,0.06), 0 0 120px rgba(167,139,250,0.03), 0 25px 50px -12px rgba(0,0,0,0.6)" }}
        >
          {/* Window chrome */}
          <div className="flex items-center gap-2 px-4 py-3 border-b border-[#27272A] bg-[#18181B]">
            <div className="flex gap-1.5">
              <div className="w-3 h-3 rounded-full bg-[#EF4444]/50" />
              <div className="w-3 h-3 rounded-full bg-[#F59E0B]/50" />
              <div className="w-3 h-3 rounded-full bg-[#22C55E]/50" />
            </div>
            <span className="ml-2 text-xs text-[#52525B] font-mono">
              quickstart.py
            </span>
            <div className="ml-auto flex items-center gap-1.5 text-[10px] text-[#52525B]">
              <span className="w-1.5 h-1.5 rounded-full bg-[#2DD4BF]/60" />
              Python
            </div>
          </div>

          {/* Code body */}
          <pre className="overflow-x-auto p-5 text-xs leading-[1.75] font-mono">
            {CODE_LINES.map((line, li) => (
              <div key={li} className="flex min-h-[1.75em]">
                <span className="select-none text-[#3F3F46] w-6 shrink-0 text-right mr-5 text-[11px] leading-[1.75]">
                  {li + 1}
                </span>
                <span className="flex-1">
                  {line.tokens.length === 0 ? (
                    <span>&nbsp;</span>
                  ) : (
                    line.tokens.map((tk, ti) => (
                      <span key={ti} style={{ color: TOKEN_COLOR[tk.c] }}>
                        {tk.t}
                      </span>
                    ))
                  )}
                </span>
              </div>
            ))}
          </pre>
        </div>

        {/* Links below code */}
        <div className="mt-5 flex items-center justify-center gap-5 text-xs text-[#52525B]">
          <a
            href="https://github.com/mnemora-db/mnemora"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 hover:text-[#A1A1AA] transition-colors"
          >
            <Github className="w-3.5 h-3.5" />
            Full SDK on GitHub
          </a>
          <span className="text-[#27272A]">·</span>
          <a
            href="/docs"
            className="flex items-center gap-1.5 hover:text-[#A1A1AA] transition-colors"
          >
            <BookOpen className="w-3.5 h-3.5" />
            Documentation
          </a>
        </div>
      </div>
    </section>
  );
}

// ─── Comparison ────────────────────────────────────────────────────────────────
function ComparisonSection() {
  return (
    <section id="compare" className="py-20 px-4 bg-[#111114]/30">
      <div className="max-w-5xl mx-auto">
        <div className="text-center mb-12">
          <span className="text-xs font-semibold text-[#52525B] uppercase tracking-widest">
            Comparison
          </span>
          <h2 className="text-2xl sm:text-3xl font-bold text-[#FAFAFA] mt-3 tracking-tight">
            How Mnemora compares
          </h2>
          <p className="text-[#71717A] text-sm mt-3 max-w-md mx-auto">
            Concrete data. No hype.
          </p>
        </div>

        <div className="overflow-x-auto rounded-xl border border-[#27272A]">
          <table className="w-full text-sm border-collapse min-w-[560px]">
            <thead>
              <tr className="border-b border-[#27272A]">
                <th className="text-left px-5 py-3.5 text-[#52525B] font-medium text-xs w-[30%] bg-[#0D0D10]">
                  Feature
                </th>
                <th className="px-4 py-3.5 text-center text-xs font-semibold text-[#2DD4BF] bg-[#2DD4BF]/[0.06] relative">
                  Mnemora
                  <div className="absolute bottom-0 left-2 right-2 h-px" style={{ background: "linear-gradient(90deg, transparent, rgba(45,212,191,0.6), transparent)", boxShadow: "0 1px 8px rgba(45,212,191,0.3)" }} />
                </th>
                <th className="px-4 py-3.5 text-center text-xs font-medium text-[#71717A] bg-[#0D0D10]">
                  Mem0
                </th>
                <th className="px-4 py-3.5 text-center text-xs font-medium text-[#71717A] bg-[#0D0D10]">
                  Zep
                </th>
                <th className="px-4 py-3.5 text-center text-xs font-medium text-[#71717A] bg-[#0D0D10]">
                  Letta
                </th>
              </tr>
            </thead>
            <tbody>
              {COMPARISON_FEATURES.map((row, i) => (
                <tr
                  key={row.feature}
                  className={`border-b border-[#27272A]/40 transition-colors duration-200 hover:bg-[#18181B]/50 ${
                    i % 2 === 0 ? "bg-[#09090B]" : "bg-[#0D0D10]"
                  }`}
                >
                  <td className="px-5 py-3 text-xs text-[#A1A1AA]">
                    {row.feature}
                  </td>
                  <td className="px-4 py-3 text-center bg-[#2DD4BF]/[0.04]">
                    <CellIcon value={row.mnemora} />
                  </td>
                  <td className="px-4 py-3 text-center">
                    <CellIcon value={row.mem0} />
                  </td>
                  <td className="px-4 py-3 text-center">
                    <CellIcon value={row.zep} />
                  </td>
                  <td className="px-4 py-3 text-center">
                    <CellIcon value={row.letta} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <p className="text-center text-xs text-[#3F3F46] mt-4">
          Data based on public documentation as of 2025. Subject to change.
        </p>
      </div>
    </section>
  );
}

// ─── Why Mnemora ───────────────────────────────────────────────────────────────
function WhySection() {
  const reasons = [
    {
      icon: Zap,
      color: "#2DD4BF",
      title: "No LLM required for CRUD",
      body: "Mem0 and Letta call an LLM for every memory operation, adding latency and token cost. Mnemora does direct database CRUD. State reads are sub-10ms. No LLM overhead, no rate limits.",
    },
    {
      icon: Server,
      color: "#38BDF8",
      title: "Truly serverless",
      body: "Every component scales to zero when idle. DynamoDB on-demand, Aurora Serverless v2, Lambda, S3. You pay per request. Estimated idle cost: ~$1/month.",
    },
    {
      icon: Users,
      color: "#A78BFA",
      title: "Multi-tenant by design",
      body: "Each API key is scoped to a tenant. Each agent gets an isolated namespace. Data is never mixed at the database layer. Built for SaaS products with multiple end-users.",
    },
    {
      icon: Activity,
      color: "#FB923C",
      title: "LangGraph native checkpoints",
      body: "Drop in MnemoraCheckpointSaver as your LangGraph checkpointer. Each thread_id maps to a Mnemora agent with optimistic locking to prevent concurrent-write data loss.",
    },
  ];

  return (
    <section className="py-20 px-4">
      <div className="max-w-5xl mx-auto">
        <div className="text-center mb-12">
          <span className="text-xs font-semibold text-[#52525B] uppercase tracking-widest">
            Why Mnemora
          </span>
          <h2 className="text-2xl sm:text-3xl font-bold text-[#FAFAFA] mt-3 tracking-tight">
            Designed different by design
          </h2>
        </div>

        <div className="grid sm:grid-cols-2 gap-4">
          {reasons.map(({ icon: Icon, color, title, body }) => (
            <div
              key={title}
              className="group relative rounded-xl p-px bg-gradient-to-b from-[#2DD4BF]/10 via-[#27272A] to-[#A78BFA]/10 transition-all duration-300 hover:-translate-y-0.5 hover:shadow-[0_0_30px_rgba(45,212,191,0.08)]"
            >
              <div className="rounded-[11px] bg-[#111114]/80 backdrop-blur-sm p-6 h-full flex gap-4">
                <div
                  className="w-9 h-9 rounded-lg shrink-0 flex items-center justify-center border mt-0.5"
                  style={{
                    background: `${color}15`,
                    borderColor: `${color}30`,
                  }}
                >
                  <Icon className="w-4 h-4" style={{ color }} />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-[#FAFAFA] mb-1.5">
                    {title}
                  </h3>
                  <p className="text-xs text-[#71717A] leading-relaxed">{body}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

// ─── FAQ ───────────────────────────────────────────────────────────────────────
function FAQSection() {
  const [open, setOpen] = useState<number | null>(null);

  return (
    <section id="faq" className="py-20 px-4 bg-[#111114]/30">
      <div className="max-w-2xl mx-auto">
        <div className="text-center mb-12">
          <span className="text-xs font-semibold text-[#52525B] uppercase tracking-widest">
            FAQ
          </span>
          <h2 className="text-2xl sm:text-3xl font-bold text-[#FAFAFA] mt-3 tracking-tight">
            Frequently asked questions
          </h2>
        </div>

        <div className="space-y-2">
          {FAQS.map((faq, i) => (
            <div
              key={i}
              className="rounded-xl border border-[#27272A] bg-[#111114] overflow-hidden"
            >
              <button
                onClick={() => setOpen(open === i ? null : i)}
                className="w-full flex items-center justify-between px-5 py-4 text-left hover:bg-[#18181B] transition-colors duration-150 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[#2DD4BF] focus-visible:ring-inset"
                aria-expanded={open === i}
              >
                <span className="text-sm font-medium text-[#FAFAFA] pr-4 leading-snug">
                  {faq.q}
                </span>
                <ChevronDown
                  className={`w-4 h-4 text-[#52525B] shrink-0 transition-transform duration-200 ${
                    open === i ? "rotate-180" : ""
                  }`}
                />
              </button>
              {open === i && (
                <div className="px-5 pb-5 border-t border-[#27272A]/50 pt-3">
                  <p className="text-sm text-[#71717A] leading-relaxed">
                    {faq.a}
                  </p>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

// ─── Blog ──────────────────────────────────────────────────────────────────────
function BlogSection() {
  return (
    <section id="blog" className="py-20 px-4">
      <div className="max-w-5xl mx-auto">
        <div className="flex items-end justify-between mb-10">
          <div>
            <span className="text-xs font-semibold text-[#52525B] uppercase tracking-widest">
              Blog
            </span>
            <h2 className="text-2xl sm:text-3xl font-bold text-[#FAFAFA] mt-2 tracking-tight">
              From the team
            </h2>
          </div>
          <a
            href="#"
            className="text-xs text-[#2DD4BF] hover:underline flex items-center gap-1"
          >
            All posts <ExternalLink className="w-3 h-3" />
          </a>
        </div>

        <div className="grid sm:grid-cols-3 gap-4">
          {BLOG_POSTS.map((post) => (
            <article
              key={post.title}
              className="rounded-xl border border-[#27272A] bg-[#111114] p-5 flex flex-col gap-3 hover:border-[#3F3F46] transition-colors duration-200"
            >
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-semibold px-2 py-0.5 rounded border border-[#2DD4BF]/30 bg-[#2DD4BF]/[0.08] text-[#2DD4BF]">
                  {post.tag}
                </span>
                <span className="text-[10px] text-[#52525B]">
                  {post.readTime} read
                </span>
              </div>
              <h3 className="text-sm font-semibold text-[#FAFAFA] leading-snug">
                {post.title}
              </h3>
              <p className="text-xs text-[#71717A] leading-relaxed flex-1">
                {post.description}
              </p>
              <div className="flex items-center gap-1.5 text-[10px] text-[#3F3F46]">
                <span className="w-1.5 h-1.5 rounded-full bg-[#27272A]" />
                Coming soon
              </div>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

// ─── Pricing ───────────────────────────────────────────────────────────────────
function PricingSection() {
  return (
    <section id="pricing" className="py-20 px-4 bg-[#111114]/30">
      <div className="max-w-5xl mx-auto">
        <div className="text-center mb-12">
          <span className="text-xs font-semibold text-[#52525B] uppercase tracking-widest">
            Pricing
          </span>
          <h2 className="text-2xl sm:text-3xl font-bold text-[#FAFAFA] mt-3 tracking-tight">
            Simple, transparent pricing
          </h2>
          <p className="text-[#71717A] text-sm mt-3 max-w-md mx-auto">
            Start free. Scale as you grow. No surprises.
          </p>
        </div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {PRICING_TIERS.map((tier) => (
            <div
              key={tier.name}
              className={`group relative rounded-xl p-px transition-all duration-300 hover:-translate-y-0.5 ${
                tier.highlight
                  ? "pricing-shimmer hover:shadow-[0_0_40px_rgba(45,212,191,0.12)]"
                  : "bg-gradient-to-b from-[#2DD4BF]/10 via-[#27272A] to-[#A78BFA]/10 hover:shadow-[0_0_30px_rgba(45,212,191,0.08)]"
              }`}
            >
              <div
                className={`rounded-[11px] p-6 flex flex-col relative h-full ${
                  tier.highlight
                    ? "bg-gradient-to-b from-[#2DD4BF]/[0.07] to-[#111114]/95 backdrop-blur-sm"
                    : "bg-[#111114]/80 backdrop-blur-sm"
                }`}
              >
                {tier.highlight && (
                  <div className="absolute -top-px left-1/2 -translate-x-1/2 px-3 py-0.5 rounded-b-md bg-[#2DD4BF] text-[#09090B] text-[10px] font-bold whitespace-nowrap">
                    Most popular
                  </div>
                )}

                <div className="mb-5 mt-2">
                  <h3 className="text-sm font-semibold text-[#FAFAFA] mb-1">
                    {tier.name}
                  </h3>
                  <p className="text-xs text-[#71717A] mb-3">{tier.description}</p>
                  <div className="flex items-baseline gap-1">
                    {tier.price === 0 ? (
                      <span className="text-2xl font-bold text-[#FAFAFA]">
                        Free
                      </span>
                    ) : (
                      <>
                        <span className="text-2xl font-bold text-[#FAFAFA]">
                          ${tier.price}
                        </span>
                        <span className="text-xs text-[#52525B]">/month</span>
                      </>
                    )}
                  </div>
                </div>

                <ul className="space-y-2.5 mb-6 flex-1">
                  {tier.features.map((f) => (
                    <li
                      key={f}
                      className="flex items-start gap-2 text-xs text-[#A1A1AA]"
                    >
                      <Check className="w-3.5 h-3.5 text-[#2DD4BF] shrink-0 mt-0.5" />
                      {f}
                    </li>
                  ))}
                </ul>

                <a
                  href={tier.href}
                  target={tier.price === 0 ? undefined : "_blank"}
                  rel={tier.price === 0 ? undefined : "noopener noreferrer"}
                  className={`w-full text-center py-2 rounded-lg text-xs font-semibold transition-all duration-150 ${
                    tier.highlight
                      ? "bg-[#2DD4BF] text-[#09090B] hover:bg-[#2DD4BF]/90"
                      : "border border-[#27272A] text-[#A1A1AA] hover:border-[#3F3F46] hover:text-[#FAFAFA]"
                  }`}
                >
                  {tier.cta}
                </a>
              </div>
            </div>
          ))}
        </div>

        <p className="text-center text-xs text-[#3F3F46] mt-6">
          All plans include TLS encryption, AWS-native infrastructure, and the
          full Python SDK. No credit card required for the free tier.
        </p>
      </div>
    </section>
  );
}

// ─── CTA banner ────────────────────────────────────────────────────────────────
function CTASection() {
  return (
    <section className="py-24 px-4 relative overflow-hidden">
      {/* Bottom glow */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background:
            "radial-gradient(ellipse 60% 80% at 50% 100%, rgba(45,212,191,0.08) 0%, transparent 70%)",
        }}
      />
      <div className="relative max-w-2xl mx-auto text-center">
        <h2 className="text-2xl sm:text-3xl font-bold text-[#FAFAFA] tracking-tight mb-4">
          Ready to give your agents memory?
        </h2>
        <p className="text-[#71717A] text-sm mb-8 max-w-md mx-auto leading-relaxed">
          Start in under 5 minutes. No infrastructure to configure. No servers
          to manage. Just memory that works.
        </p>
        <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
          <Link
            href="/dashboard"
            className="flex items-center gap-2 px-6 py-3 rounded-lg bg-[#2DD4BF] text-[#09090B] text-sm font-semibold hover:bg-[#2DD4BF]/90 transition-all duration-150 shadow-lg shadow-[#2DD4BF]/20"
          >
            Get started free
            <ArrowRight className="w-4 h-4" />
          </Link>
          <a
            href="https://github.com/mnemora-db/mnemora"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 px-6 py-3 rounded-lg border border-[#27272A] text-[#A1A1AA] text-sm font-medium hover:border-[#3F3F46] hover:text-[#FAFAFA] transition-all duration-150"
          >
            <Github className="w-4 h-4" />
            Self-host with CDK
          </a>
        </div>
      </div>
    </section>
  );
}

// ─── Footer ────────────────────────────────────────────────────────────────────
function Footer() {
  return (
    <footer className="border-t border-[#27272A] bg-[#111114]/50">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-12">
        <div className="flex flex-col sm:flex-row items-start justify-between gap-10">
          {/* Brand */}
          <div className="max-w-xs">
            <Link
              href="/"
              className="flex items-center gap-2 text-[#FAFAFA] font-semibold mb-3"
            >
              <div className="w-6 h-6 rounded flex items-center justify-center bg-[#18181B] border border-[#27272A]">
                <MnemoraLogo size={13} />
              </div>
              mnemora
            </Link>
            <p className="text-xs text-[#52525B] leading-relaxed">
              Serverless memory infrastructure for AI agents. One API, four
              memory types, zero servers.
            </p>
          </div>

          {/* Links */}
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-8 text-xs">
            <div>
              <p className="text-[#71717A] font-semibold mb-3 uppercase tracking-wider text-[10px]">
                Product
              </p>
              <div className="space-y-2.5">
                <a href="#features" className="block text-[#52525B] hover:text-[#A1A1AA] transition-colors">Features</a>
                <a href="#pricing" className="block text-[#52525B] hover:text-[#A1A1AA] transition-colors">Pricing</a>
                <a href="#compare" className="block text-[#52525B] hover:text-[#A1A1AA] transition-colors">Compare</a>
              </div>
            </div>
            <div>
              <p className="text-[#71717A] font-semibold mb-3 uppercase tracking-wider text-[10px]">
                Developers
              </p>
              <div className="space-y-2.5">
                <a href="/docs" className="block text-[#52525B] hover:text-[#A1A1AA] transition-colors">Docs</a>
                <a href="/docs/api-reference" className="block text-[#52525B] hover:text-[#A1A1AA] transition-colors">API Reference</a>
                <a
                  href="https://github.com/mnemora-db/mnemora"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1.5 text-[#52525B] hover:text-[#A1A1AA] transition-colors"
                >
                  <Github className="w-3 h-3" /> GitHub
                </a>
              </div>
            </div>
            <div>
              <p className="text-[#71717A] font-semibold mb-3 uppercase tracking-wider text-[10px]">
                Company
              </p>
              <div className="space-y-2.5">
                <a href="#blog" className="block text-[#52525B] hover:text-[#A1A1AA] transition-colors">Blog</a>
                <a href="#" className="block text-[#52525B] hover:text-[#A1A1AA] transition-colors">Privacy</a>
                <a href="#" className="block text-[#52525B] hover:text-[#A1A1AA] transition-colors">Terms</a>
              </div>
            </div>
          </div>
        </div>

        {/* Bottom row */}
        <div className="mt-10 pt-6 border-t border-[#27272A]/50 flex flex-col sm:flex-row items-center justify-between gap-3 text-[10px] text-[#3F3F46]">
          <span>© {new Date().getFullYear()} Mnemora. MIT / BSL-1.1 Licensed.</span>
          <div className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-[#2DD4BF]" />
            <span>All systems operational</span>
          </div>
        </div>
      </div>
    </footer>
  );
}

// ─── Section divider ──────────────────────────────────────────────────────────
function SectionDivider() {
  return (
    <div className="relative h-px">
      <div
        className="absolute inset-0"
        style={{
          background: "linear-gradient(90deg, transparent, rgba(45,212,191,0.2), transparent)",
        }}
      />
      <div
        className="absolute inset-0"
        style={{
          background: "linear-gradient(90deg, transparent, rgba(45,212,191,0.15), transparent)",
          filter: "blur(4px)",
        }}
      />
    </div>
  );
}

// ─── Main export ───────────────────────────────────────────────────────────────
export default function LandingPage() {
  return (
    <div className="min-h-screen bg-[#09090B]">
      <Navbar />
      <main>
        <HeroSection />
        <TrustStrip />
        <ProblemSection />
        <SectionDivider />
        <SolutionSection />
        <SectionDivider />
        <CodeSection />
        <SectionDivider />
        <ComparisonSection />
        <SectionDivider />
        <WhySection />
        <SectionDivider />
        <FAQSection />
        <SectionDivider />
        <BlogSection />
        <SectionDivider />
        <PricingSection />
        <SectionDivider />
        <CTASection />
      </main>
      <Footer />
    </div>
  );
}
