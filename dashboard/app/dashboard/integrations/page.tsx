export const dynamic = "force-dynamic";

import Link from "next/link";
import { cn } from "@/lib/utils";
import { NotifyButton } from "./notify-button";

const connectors = [
  {
    name: "HubSpot",
    icon: "🟠",
    description: "Sync contacts, companies, deals, and tickets from HubSpot CRM",
    objects: ["contacts", "companies", "deals", "tickets"],
    status: "available" as const,
    href: "/dashboard/integrations/hubspot",
  },
  {
    name: "Salesforce",
    icon: "☁️",
    description: "Sync contacts, accounts, opportunities, and cases from Salesforce",
    objects: ["contacts", "accounts", "opportunities", "cases"],
    status: "coming_soon" as const,
    href: "/dashboard/integrations/salesforce",
  },
  {
    name: "Odoo",
    icon: "🟣",
    description: "Sync partners, leads, tickets, and orders from Odoo ERP",
    objects: ["partners", "leads", "tickets", "orders"],
    status: "coming_soon" as const,
    href: "/dashboard/integrations/odoo",
  },
  {
    name: "Zoho CRM",
    icon: "🔴",
    description: "Sync contacts, accounts, deals, and tickets from Zoho CRM",
    objects: ["contacts", "accounts", "deals", "tickets"],
    status: "coming_soon" as const,
    href: "/dashboard/integrations/zoho",
  },
];

export default function IntegrationsPage() {
  return (
    <div className="space-y-8 max-w-5xl">
      <div>
        <h1 className="text-[22px] font-semibold text-[#FAFAFA] tracking-tight">
          Integrations
        </h1>
        <p className="text-sm text-[#A1A1AA] mt-1">
          Connect your CRM and ERP to give your agents real customer context.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {connectors.map((c) => (
          <div
            key={c.name}
            className="rounded-xl border border-[#27272A] bg-[#18181B] p-6 flex flex-col gap-4 hover:border-[#3F3F46] transition-colors duration-150"
          >
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-3">
                <span className="text-2xl">{c.icon}</span>
                <h3 className="text-base font-semibold text-[#FAFAFA]">
                  {c.name}
                </h3>
              </div>
              <span
                className={cn(
                  "text-[10px] font-semibold px-2 py-0.5 rounded-full border",
                  c.status === "available"
                    ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                    : "bg-[#27272A]/50 text-[#71717A] border-[#3F3F46]"
                )}
              >
                {c.status === "available" ? "Available" : "Coming Soon"}
              </span>
            </div>

            <p className="text-sm text-[#A1A1AA] leading-relaxed">
              {c.description}
            </p>

            <div className="flex flex-wrap gap-1.5">
              {c.objects.map((obj) => (
                <span
                  key={obj}
                  className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-teal-500/10 text-teal-400 border border-teal-500/20"
                >
                  {obj}
                </span>
              ))}
            </div>

            <div className="mt-auto pt-2">
              {c.status === "available" ? (
                <Link
                  href={c.href}
                  className="inline-flex items-center justify-center rounded-md bg-[#2DD4BF] px-4 py-2 text-sm font-medium text-[#09090B] hover:bg-teal-300 transition-colors duration-150"
                >
                  Connect
                </Link>
              ) : (
                <NotifyButton connectorName={c.name} />
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
