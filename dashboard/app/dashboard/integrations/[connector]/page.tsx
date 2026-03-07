export const dynamic = "force-dynamic";

import { redirect } from "next/navigation";
import { ComingSoonForm } from "./coming-soon-form";

const CONNECTOR_META: Record<string, { icon: string; display: string; description: string }> = {
  salesforce: { icon: "☁️", display: "Salesforce", description: "Sync contacts, accounts, opportunities, and cases from Salesforce." },
  odoo: { icon: "🟣", display: "Odoo", description: "Sync partners, leads, tickets, and orders from Odoo ERP." },
  zoho: { icon: "🔴", display: "Zoho CRM", description: "Sync contacts, accounts, deals, and tickets from Zoho CRM." },
};

export default async function ConnectorPage({ params }: { params: Promise<{ connector: string }> }) {
  const { connector } = await params;

  if (connector === "hubspot") {
    redirect("/dashboard/integrations/hubspot");
  }

  const meta = CONNECTOR_META[connector] || { icon: "🔌", display: connector, description: "Integration details." };

  return (
    <div className="max-w-lg mx-auto space-y-8">
      <div className="text-center space-y-3 pt-8">
        <span className="text-5xl">{meta.icon}</span>
        <h1 className="text-[22px] font-semibold text-[#FAFAFA] tracking-tight">
          {meta.display}
        </h1>
        <p className="text-sm text-[#A1A1AA]">{meta.description}</p>
      </div>

      <div className="rounded-xl border border-[#27272A] bg-[#18181B] p-6 text-center space-y-4">
        <p className="text-sm text-[#A1A1AA]">
          We&apos;re building this integration. Enter your email to be notified when it&apos;s ready.
        </p>
        <ComingSoonForm connectorName={meta.display} />
      </div>
    </div>
  );
}
