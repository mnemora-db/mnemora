import Link from "next/link";

export const metadata = {
  title: "Privacy Policy — Mnemora",
  description: "Privacy Policy for the Mnemora memory infrastructure platform.",
};

export default function PrivacyPage() {
  return (
    <div className="min-h-screen bg-[#09090B] text-zinc-300">
      {/* Nav */}
      <header className="border-b border-[#27272A]/80 bg-[#09090B]/90 backdrop-blur-md">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 h-14 flex items-center">
          <Link
            href="/"
            className="flex items-center gap-2 text-[#FAFAFA] font-semibold tracking-tight"
          >
            <div className="w-7 h-7 rounded flex items-center justify-center bg-[#18181B] border border-[#27272A]">
              <svg width="16" height="16" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M3 16V4L10 11L17 4V16" stroke="#2DD4BF" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
            <span>mnemora</span>
          </Link>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 sm:px-6 py-16">
        <h1 className="text-3xl font-bold text-[#FAFAFA] tracking-tight mb-2">
          Privacy Policy
        </h1>
        <p className="text-sm text-[#52525B] mb-12">Last updated: March 4, 2026</p>

        <div className="space-y-10 text-sm leading-relaxed">
          <p>
            Mnemora (&ldquo;we&rdquo;, &ldquo;us&rdquo;, &ldquo;our&rdquo;) is operated by Isaac
            Guti&eacute;rrez Brugada. This Privacy Policy explains how we collect, use, and protect
            your information when you use the Mnemora service, including the API, SDK, and dashboard
            at mnemora.dev.
          </p>

          <section>
            <h2 className="text-lg font-semibold text-[#FAFAFA] mb-3">1. Information We Collect</h2>

            <h3 className="text-sm font-semibold text-[#FAFAFA] mt-4 mb-2">GitHub Profile Data</h3>
            <p>
              When you sign in via GitHub OAuth, we receive your GitHub username, email address, and
              avatar URL. This data is used to create and identify your account.
            </p>

            <h3 className="text-sm font-semibold text-[#FAFAFA] mt-4 mb-2">API Usage Data</h3>
            <p>
              We collect aggregated usage metrics including API calls per day/month, endpoints used,
              and response latencies. This data is used to enforce tier limits and monitor service
              health.
            </p>

            <h3 className="text-sm font-semibold text-[#FAFAFA] mt-4 mb-2">Memory Data</h3>
            <p>
              Data stored by your AI agents through the Mnemora API (working state, semantic
              memories, episodic logs, procedural definitions) is your data. We store it to provide
              the Service and do not access, analyze, or use it for any other purpose.
            </p>

            <h3 className="text-sm font-semibold text-[#FAFAFA] mt-4 mb-2">Payment Information</h3>
            <p>
              Payment processing is handled by Creala. We do not store credit card numbers or
              payment credentials. We receive only transaction confirmation and subscription status
              from Creala.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-[#FAFAFA] mb-3">2. How We Use Information</h2>
            <ul className="list-disc list-inside space-y-1.5 text-zinc-400">
              <li>Provide, maintain, and improve the Service</li>
              <li>Monitor usage to enforce tier limits and prevent abuse</li>
              <li>Send service-related communications (downtime notices, security alerts)</li>
              <li>Respond to support requests</li>
            </ul>
            <p className="mt-3 font-medium text-[#FAFAFA]">
              We do NOT sell your data to third parties. We do NOT use your data for advertising.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-[#FAFAFA] mb-3">3. Data Storage</h2>
            <p>
              All data is stored in AWS us-east-1 region using DynamoDB, Aurora PostgreSQL, and S3.
              All data is encrypted at rest (AES-256 for DynamoDB and S3, Postgres TDE for Aurora)
              and encrypted in transit via TLS. API keys are SHA-256 hashed before storage and are
              never stored in plaintext.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-[#FAFAFA] mb-3">4. Data Retention</h2>
            <ul className="list-disc list-inside space-y-1.5 text-zinc-400">
              <li>Account data is retained while your account is active</li>
              <li>Memory data is permanently deleted upon account deletion</li>
              <li>Service logs are retained for 30 days and then automatically purged</li>
              <li>Aggregated, anonymized usage statistics may be retained indefinitely</li>
            </ul>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-[#FAFAFA] mb-3">5. Your Rights</h2>
            <ul className="list-disc list-inside space-y-1.5 text-zinc-400">
              <li>
                <span className="font-medium text-zinc-300">Access:</span> You can access all your
                data through the Mnemora API at any time
              </li>
              <li>
                <span className="font-medium text-zinc-300">Delete:</span> You can delete your data
                through the API or by contacting us at{" "}
                <a href="mailto:isaac@mnemora.dev" className="text-[#2DD4BF] hover:underline">
                  isaac@mnemora.dev
                </a>
              </li>
              <li>
                <span className="font-medium text-zinc-300">Export:</span> The API provides full
                access to all your stored data for export purposes
              </li>
              <li>
                <span className="font-medium text-zinc-300">Portability:</span> All data formats
                are documented and use standard JSON
              </li>
            </ul>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-[#FAFAFA] mb-3">6. Third-Party Services</h2>
            <p className="mb-3">We use the following third-party services to operate Mnemora:</p>
            <ul className="list-disc list-inside space-y-1.5 text-zinc-400">
              <li>
                <span className="font-medium text-zinc-300">AWS</span> — Cloud infrastructure
                (DynamoDB, Aurora, S3, Lambda)
              </li>
              <li>
                <span className="font-medium text-zinc-300">Vercel</span> — Dashboard hosting
              </li>
              <li>
                <span className="font-medium text-zinc-300">GitHub</span> — Authentication via
                OAuth
              </li>
              <li>
                <span className="font-medium text-zinc-300">Creala</span> — Payment processing
              </li>
              <li>
                <span className="font-medium text-zinc-300">Amazon Bedrock (Titan)</span> —
                Embedding generation for semantic memory. Text is processed to generate vectors but
                is not stored by the embedding service.
              </li>
            </ul>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-[#FAFAFA] mb-3">
              7. Children&apos;s Privacy
            </h2>
            <p>
              Mnemora is not intended for use by individuals under the age of 13. We do not
              knowingly collect personal information from children. If we become aware that we have
              collected data from a child under 13, we will take steps to delete it promptly.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-[#FAFAFA] mb-3">8. Changes to This Policy</h2>
            <p>
              We may update this Privacy Policy from time to time. Material changes will be
              communicated via the dashboard or email. The &ldquo;Last updated&rdquo; date at the
              top of this page reflects the most recent revision.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-[#FAFAFA] mb-3">9. Contact</h2>
            <p>
              For questions about this Privacy Policy or to exercise your data rights, contact us
              at{" "}
              <a href="mailto:isaac@mnemora.dev" className="text-[#2DD4BF] hover:underline">
                isaac@mnemora.dev
              </a>
              .
            </p>
          </section>
        </div>

        <div className="mt-16 pt-8 border-t border-[#27272A]/50 text-xs text-[#3F3F46]">
          <p>
            See also:{" "}
            <Link href="/terms" className="text-[#2DD4BF] hover:underline">
              Terms of Service
            </Link>
          </p>
        </div>
      </main>
    </div>
  );
}
