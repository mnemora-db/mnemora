import { ApiCallsChart } from "@/components/charts/api-calls-chart";
import { EndpointChart } from "@/components/charts/endpoint-chart";
import { StorageChart } from "@/components/charts/storage-chart";
import {
  mockChartData,
  mockEndpointStats,
  mockStorageBreakdown,
  mockCostEstimates,
} from "@/lib/mock-data";

function totalCost(costs: { cost: number }[]): number {
  return costs.reduce((sum, c) => sum + c.cost, 0);
}

export default function UsagePage() {
  const total = totalCost(mockCostEstimates);

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-[22px] font-semibold text-[#FAFAFA] tracking-tight">
          Usage
        </h1>
        <p className="mt-0.5 text-sm text-[#71717A]">
          Current billing period: March 1–31, 2026.
        </p>
      </div>

      {/* API calls over time */}
      <section aria-label="API calls over time">
        <div className="rounded-md border border-[#27272A] bg-[#18181B]">
          <div className="px-5 py-4 border-b border-[#27272A]">
            <h2 className="text-sm font-medium text-[#FAFAFA]">
              API Calls — Last 30 Days
            </h2>
            <p className="text-xs text-[#71717A] mt-0.5">
              Daily request volume across all endpoints.
            </p>
          </div>
          <div className="px-5 py-5">
            <ApiCallsChart data={mockChartData} />
          </div>
        </div>
      </section>

      {/* Two-chart row */}
      <section
        aria-label="Endpoint and storage breakdown"
        className="grid grid-cols-1 gap-3 lg:grid-cols-2"
      >
        {/* Calls by endpoint */}
        <div className="rounded-md border border-[#27272A] bg-[#18181B]">
          <div className="px-5 py-4 border-b border-[#27272A]">
            <h2 className="text-sm font-medium text-[#FAFAFA]">
              Calls by Endpoint
            </h2>
            <p className="text-xs text-[#71717A] mt-0.5">
              Request distribution this month.
            </p>
          </div>
          <div className="px-5 py-5">
            <EndpointChart data={mockEndpointStats} />
          </div>
        </div>

        {/* Storage breakdown */}
        <div className="rounded-md border border-[#27272A] bg-[#18181B]">
          <div className="px-5 py-4 border-b border-[#27272A]">
            <h2 className="text-sm font-medium text-[#FAFAFA]">
              Storage Breakdown
            </h2>
            <p className="text-xs text-[#71717A] mt-0.5">
              Total: 2.4 GB across all storage backends.
            </p>
          </div>
          <div className="px-5 py-5">
            <StorageChart data={mockStorageBreakdown} />
          </div>
        </div>
      </section>

      {/* Cost estimate */}
      <section aria-label="Cost estimate">
        <div className="rounded-md border border-[#27272A] bg-[#18181B]">
          <div className="px-5 py-4 border-b border-[#27272A]">
            <h2 className="text-sm font-medium text-[#FAFAFA]">
              Cost Estimate
            </h2>
            <p className="text-xs text-[#71717A] mt-0.5">
              Estimates based on current usage patterns.
            </p>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-sm" aria-label="Cost estimates by service">
              <thead>
                <tr className="border-b border-[#27272A]">
                  <th
                    scope="col"
                    className="px-5 py-3 text-left text-[10px] font-medium text-[#71717A] uppercase tracking-wide"
                  >
                    Service
                  </th>
                  <th
                    scope="col"
                    className="px-5 py-3 text-left text-[10px] font-medium text-[#71717A] uppercase tracking-wide"
                  >
                    Detail
                  </th>
                  <th
                    scope="col"
                    className="px-5 py-3 text-right text-[10px] font-medium text-[#71717A] uppercase tracking-wide"
                  >
                    Estimated Cost
                  </th>
                </tr>
              </thead>
              <tbody>
                {mockCostEstimates.map((item) => (
                  <tr
                    key={item.service}
                    className="border-b border-[#27272A] last:border-0"
                  >
                    <td className="px-5 py-3 text-[#FAFAFA] font-medium">
                      {item.service}
                    </td>
                    <td className="px-5 py-3 text-[#71717A] text-xs">
                      {item.detail}
                    </td>
                    <td className="px-5 py-3 text-right font-mono text-[#A1A1AA]">
                      ~${item.cost.toFixed(2)}
                    </td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr className="border-t border-[#3F3F46]">
                  <td
                    colSpan={2}
                    className="px-5 py-3 text-sm font-semibold text-[#FAFAFA]"
                  >
                    Total
                  </td>
                  <td className="px-5 py-3 text-right font-mono font-semibold text-[#FAFAFA]">
                    ~${total.toFixed(2)}/month
                  </td>
                </tr>
              </tfoot>
            </table>
          </div>
        </div>
      </section>
    </div>
  );
}
