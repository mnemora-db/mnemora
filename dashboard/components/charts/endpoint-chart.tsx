"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import type { EndpointStat } from "@/lib/mock-data";

interface EndpointChartProps {
  data: EndpointStat[];
}

interface TooltipPayload {
  value: number;
  payload: EndpointStat;
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: TooltipPayload[];
}

function CustomTooltip({ active, payload }: CustomTooltipProps) {
  if (!active || !payload || payload.length === 0) return null;
  const item = payload[0];

  return (
    <div className="rounded-md border border-[#3F3F46] bg-[#18181B] px-3 py-2">
      <p className="text-xs font-mono text-[#A1A1AA] mb-1">
        {item.payload.endpoint}
      </p>
      <p className="text-sm font-mono font-medium text-[#FAFAFA]">
        {item.value.toLocaleString()} calls
      </p>
    </div>
  );
}

function truncateEndpoint(endpoint: string): string {
  if (endpoint.length <= 24) return endpoint;
  return endpoint.slice(0, 22) + "…";
}

export function EndpointChart({ data }: EndpointChartProps) {
  return (
    <div
      className="w-full h-56"
      role="img"
      aria-label="API calls by endpoint horizontal bar chart"
    >
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={data}
          layout="vertical"
          margin={{ top: 0, right: 8, left: 8, bottom: 0 }}
        >
          <CartesianGrid
            strokeDasharray="3 3"
            stroke="#27272A"
            horizontal={false}
          />
          <XAxis
            type="number"
            tick={{ fill: "#71717A", fontSize: 11, fontFamily: "var(--font-geist-mono)" }}
            tickLine={false}
            axisLine={false}
            tickFormatter={(v: number) =>
              v >= 1000 ? `${(v / 1000).toFixed(1)}k` : String(v)
            }
          />
          <YAxis
            type="category"
            dataKey="endpoint"
            tick={{ fill: "#71717A", fontSize: 10, fontFamily: "var(--font-geist-mono)" }}
            tickLine={false}
            axisLine={false}
            width={130}
            tickFormatter={truncateEndpoint}
          />
          <Tooltip
            content={<CustomTooltip />}
            cursor={{ fill: "rgba(255,255,255,0.03)" }}
          />
          <Bar dataKey="calls" radius={[0, 2, 2, 0]} maxBarSize={12}>
            {data.map((entry, index) => (
              <Cell
                key={entry.endpoint}
                fill={index === 0 ? "#2DD4BF" : "#3F3F46"}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
