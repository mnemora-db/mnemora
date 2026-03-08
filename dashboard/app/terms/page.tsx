import Link from "next/link";

export const metadata = {
  title: "Terms of Service — Mnemora",
  description: "Terms of Service for the Mnemora memory infrastructure platform.",
};

export default function TermsPage() {
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
          Terms of Service
        </h1>
        <p className="text-sm text-[#52525B] mb-12">Last updated: March 4, 2026</p>

        <div className="space-y-10 text-sm leading-relaxed">
          <section>
            <h2 className="text-lg font-semibold text-[#FAFAFA] mb-3">1. Acceptance of Terms</h2>
            <p>
              By accessing or using the Mnemora service (&ldquo;Service&rdquo;), including the API, SDK, and
              dashboard at mnemora.dev, you agree to be bound by these Terms of Service
              (&ldquo;Terms&rdquo;). If you do not agree to these Terms, do not use the Service.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-[#FAFAFA] mb-3">2. Description of Service</h2>
            <p>
              Mnemora is an open-source serverless memory database for AI agents, operated by Isaac
              Guti&eacute;rrez Brugada. The Service consists of a hosted REST API, a Python SDK, and a
              web dashboard at mnemora.dev. Mnemora provides four types of persistent memory — working,
              semantic, episodic, and procedural — for AI agent applications.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-[#FAFAFA] mb-3">3. Accounts and API Keys</h2>
            <p>
              To use the Service, you must authenticate via GitHub OAuth. You are responsible for
              maintaining the security of your account and API keys. API keys prefixed with{" "}
              <code className="text-[#2DD4BF] bg-[#2DD4BF]/10 px-1 py-0.5 rounded text-xs">mnm_</code>{" "}
              are hashed before storage and cannot be retrieved after creation. You must not share
              your API keys or allow unauthorized access to your account.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-[#FAFAFA] mb-3">4. Free and Paid Tiers</h2>
            <p>
              Mnemora offers free and paid subscription tiers. Current pricing and tier limits are
              available on the{" "}
              <Link href="/#pricing" className="text-[#2DD4BF] hover:underline">
                pricing page
              </Link>
              . Paid subscriptions are processed through Creala, our payment processor. Subscriptions
              renew monthly unless cancelled. Refunds are handled on a case-by-case basis.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-[#FAFAFA] mb-3">5. Acceptable Use</h2>
            <p className="mb-3">You agree not to:</p>
            <ul className="list-disc list-inside space-y-1.5 text-zinc-400">
              <li>Use the Service for any illegal purpose or to store illegal content</li>
              <li>Attempt to circumvent rate limits or tier restrictions</li>
              <li>Interfere with or disrupt the Service infrastructure</li>
              <li>Reverse-engineer the hosted Service (the open-source code is freely available)</li>
              <li>Use the Service to store personally identifiable information of third parties without their consent</li>
              <li>Resell access to the Service without authorization</li>
            </ul>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-[#FAFAFA] mb-3">6. Data and Privacy</h2>
            <p>
              Your use of the Service is also governed by our{" "}
              <Link href="/privacy" className="text-[#2DD4BF] hover:underline">
                Privacy Policy
              </Link>
              , which describes how we collect, use, and protect your data.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-[#FAFAFA] mb-3">7. Open Source</h2>
            <p>
              The Mnemora API handlers and Python SDK are released under the MIT license. The hosted
              Service at mnemora.dev is a separate offering that provides managed infrastructure,
              support, and guaranteed uptime for paid tiers. Self-hosting the open-source code is
              permitted under the license terms.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-[#FAFAFA] mb-3">8. Intellectual Property</h2>
            <p>
              All data you store through the Service belongs to you. You retain full ownership of
              your memory data, agent configurations, and any content processed through the API.
              Mnemora infrastructure, branding, documentation, and the hosted Service are the
              intellectual property of Mnemora and its operator.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-[#FAFAFA] mb-3">9. Disclaimers</h2>
            <p>
              The Service is provided &ldquo;as is&rdquo; and &ldquo;as available&rdquo; without
              warranties of any kind, either express or implied. No service level agreement (SLA) is
              provided for the Free tier. Paid tiers include reasonable uptime commitments as
              described on the pricing page. We do not guarantee that the Service will be
              uninterrupted, error-free, or that data will never be lost.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-[#FAFAFA] mb-3">10. Limitation of Liability</h2>
            <p>
              To the maximum extent permitted by applicable law, Mnemora and its operator shall not
              be liable for any indirect, incidental, special, consequential, or punitive damages,
              or any loss of profits or revenues, whether incurred directly or indirectly, or any
              loss of data, use, goodwill, or other intangible losses resulting from your use of
              the Service.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-[#FAFAFA] mb-3">11. Termination</h2>
            <p>
              We may suspend or terminate your account at any time if you violate these Terms. Upon
              termination, your right to use the Service ceases immediately. We will make reasonable
              efforts to allow you to export your data before deletion, except in cases of abuse.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-[#FAFAFA] mb-3">12. Changes to Terms</h2>
            <p>
              We may update these Terms from time to time. Material changes will be communicated
              via the dashboard or email. Continued use of the Service after changes constitutes
              acceptance of the updated Terms.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-[#FAFAFA] mb-3">13. Governing Law</h2>
            <p>
              These Terms shall be governed by and construed in accordance with the laws of the
              Republic of Paraguay, without regard to conflict of law principles.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-[#FAFAFA] mb-3">14. Contact</h2>
            <p>
              For questions about these Terms, contact us at{" "}
              <a href="mailto:isaac@mnemora.dev" className="text-[#2DD4BF] hover:underline">
                isaac@mnemora.dev
              </a>
              .
            </p>
          </section>
        </div>
      </main>
    </div>
  );
}
