# Email Outreach Templates

For direct outreach to AI agent developers and framework maintainers.
Tone: personal, first-person, value-first. Ask for feedback, not signup.

---

## Subject Line Options

**Option A (problem-first):**
Your LangGraph agents lose memory between sessions — built something about it

**Option B (direct):**
Open-source memory layer for AI agents — would love your feedback

**Option C (specific to framework maintainers):**
Built a persistent memory backend for LangGraph — wanted to show you

---

## Email Template

**To:** [Name]
**Subject:** [Choose one above]

---

Hi [Name],

I noticed [WHY I'M REACHING OUT TO YOU SPECIFICALLY — see note below]. That's why I wanted to share something I've been building.

The problem I kept running into: AI agents are stateless between sessions by default. Developers who need persistence end up stitching together 3-5 separate databases — Redis for state, Pinecone for vectors, Postgres for history, S3 for logs. It works, but the operational overhead is high and there's no unified query layer.

I built Mnemora to address this: one REST API backed by four memory types — working (DynamoDB), semantic (pgvector + Bedrock embeddings), episodic (time-series logs), and procedural (Postgres, schema deployed, SDK in v0.2).

The part most relevant to your work: the SDK ships with a `MnemoraCheckpointSaver` for LangGraph and a `MnemoraMemory` class for LangChain, both built against the actual base class interfaces. No LLM call is required for CRUD — that's a meaningful difference from Mem0 and Letta which require a model call per write.

It's open source (MIT license for the SDK). You can deploy the full AWS stack yourself with `npx cdk deploy`.

GitHub: https://github.com/mnemora-dev/mnemora

I'm not looking for signups — I'd genuinely like to know if the design makes sense for the problems you're actually solving, or where it falls short.

[Your name]

---

## "Why I'm Reaching Out to You Specifically" — Placeholder Examples

Fill this section with a single specific, honest sentence. Examples:

- **Framework maintainer:** "I saw your talk on LangGraph persistence patterns at [conference] — the checkpoint compatibility question you raised is exactly what this is trying to solve."
- **Developer with related OSS project:** "I came across [their project] on GitHub and it looks like you've solved the same statelessness problem with a different approach — I'm curious how you thought about the trade-offs."
- **Active community contributor:** "You've answered a lot of questions in the LangChain Discord about memory persistence, so you've probably seen the full range of how people try to solve this."
- **Researcher:** "I read your paper on [topic] — the memory representation question in section 3 is related to the design choices I made in the semantic layer here."

Do not write a generic "I follow your work" sentence. If you cannot fill this with something specific, do not send the email.

---

## What Not to Include

- No attachments. GitHub link is sufficient.
- No pricing discussion in the first email.
- No "hope this finds you well" or similar filler.
- Do not ask them to sign up, share, or post. Ask for feedback only.
- Do not use their follower count or fame as a reason for the outreach. "You have 50K followers" is not a reason. "You've publicly worked on this specific problem" is.

---

## Follow-up (if no response after 7 days)

Subject: Re: [original subject]

Hi [Name],

Just following up in case the first email got buried. No pressure — I know you're busy.

If Mnemora isn't relevant to what you're working on, that's useful to know too.

[Your name]

Keep the follow-up to two sentences. One follow-up only.
