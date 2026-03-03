import type { Metadata } from "next";
import LandingPage from "@/components/landing/LandingPage";

export const metadata: Metadata = {
  title: "Mnemora — Serverless Memory for AI Agents",
  description:
    "One API for four memory types. Working, semantic, episodic, and procedural memory for AI agents — serverless, AWS-native, zero infrastructure to manage.",
  keywords: [
    "AI agent memory",
    "LLM memory",
    "serverless memory",
    "vector search",
    "LangGraph memory",
    "episodic memory",
    "semantic memory",
    "working memory",
    "agent persistence",
    "mnemora",
    "pgvector",
    "AWS serverless",
  ],
  openGraph: {
    title: "Mnemora — Serverless Memory for AI Agents",
    description:
      "One API. Four memory types. Zero infrastructure. Give your AI agents persistent memory in minutes, not months.",
    type: "website",
    url: "https://mnemora.dev",
  },
  twitter: {
    card: "summary_large_image",
    title: "Mnemora — Serverless Memory for AI Agents",
    description:
      "One API. Four memory types. Zero infrastructure. Give your AI agents persistent memory in minutes.",
  },
};

const jsonLd = {
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "SoftwareApplication",
      "@id": "https://mnemora.dev/#software",
      name: "Mnemora",
      applicationCategory: "DeveloperApplication",
      operatingSystem: "Cloud",
      description:
        "Serverless memory infrastructure for AI agents. One API for working, semantic, episodic, and procedural memory. Built on AWS-native infrastructure.",
      url: "https://mnemora.dev",
      offers: [
        {
          "@type": "Offer",
          price: "0",
          priceCurrency: "USD",
          name: "Free",
          description: "10,000 ops/month, 1 agent, 500MB storage",
        },
        {
          "@type": "Offer",
          price: "19",
          priceCurrency: "USD",
          name: "Starter",
          description: "100,000 ops/month, 10 agents, 5GB storage",
        },
        {
          "@type": "Offer",
          price: "79",
          priceCurrency: "USD",
          name: "Pro",
          description: "1M ops/month, unlimited agents, 50GB storage",
        },
        {
          "@type": "Offer",
          price: "299",
          priceCurrency: "USD",
          name: "Scale",
          description: "10M ops/month, unlimited agents, 500GB storage",
        },
      ],
      programmingLanguage: ["Python", "JavaScript", "TypeScript"],
      codeRepository: "https://github.com/mnemora-db/mnemora",
      license: "https://opensource.org/licenses/MIT",
    },
    {
      "@type": "Organization",
      "@id": "https://mnemora.dev/#org",
      name: "Mnemora",
      url: "https://mnemora.dev",
      sameAs: ["https://github.com/mnemora-db/mnemora"],
    },
    {
      "@type": "WebSite",
      "@id": "https://mnemora.dev/#website",
      url: "https://mnemora.dev",
      name: "Mnemora",
      publisher: { "@id": "https://mnemora.dev/#org" },
    },
    {
      "@type": "FAQPage",
      mainEntity: [
        {
          "@type": "Question",
          name: "What exactly is Mnemora?",
          acceptedAnswer: {
            "@type": "Answer",
            text: "Mnemora is a serverless memory infrastructure for AI agents. It provides four types of memory — working (key-value state), semantic (vector similarity search), episodic (time-series event log), and procedural (tool definitions and rules) — all behind a single REST API and Python SDK.",
          },
        },
        {
          "@type": "Question",
          name: "How is Mnemora different from Mem0 or Zep?",
          acceptedAnswer: {
            "@type": "Answer",
            text: "Mnemora does direct CRUD with sub-10ms state reads, requiring no LLM call. Mem0 and Letta require an LLM call for every memory operation. Mnemora also supports 4 memory types, is truly serverless (scales to zero), and natively supports LangGraph checkpoints.",
          },
        },
        {
          "@type": "Question",
          name: "Is it really serverless?",
          acceptedAnswer: {
            "@type": "Answer",
            text: "Yes. Mnemora is built entirely on AWS serverless services: DynamoDB on-demand, Aurora Serverless v2, Lambda ARM64, and S3. You pay per request with no idle compute costs.",
          },
        },
        {
          "@type": "Question",
          name: "Can I self-host Mnemora?",
          acceptedAnswer: {
            "@type": "Answer",
            text: "Yes. Deploy to your AWS account with npx cdk deploy. This provisions DynamoDB, Aurora Serverless v2 with pgvector, Lambda, API Gateway, S3, and CloudWatch dashboards. Estimated idle cost is ~$15/month.",
          },
        },
      ],
    },
  ],
};

export default function HomePage() {
  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      <LandingPage />
    </>
  );
}
