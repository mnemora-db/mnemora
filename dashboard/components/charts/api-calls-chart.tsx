"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import type { ChartDataPoint } from "@/lib/mock-data";

interface ApiCallsChartProps {
  data: ChartDataPoint[];
}

interface TooltipPayload {
  value: number;
  name: string;
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: TooltipPayload[];
  label?: string;
}

function CustomTooltip({ active, payload, label }: CustomTooltipProps) {
  if (!active || !payload || payload.length === 0) return null;

  return (
    <div className="rounded-md border border-[#3F3F46] bg-[#18181B] px-3 py-2 shadow-none">
      <p className="text-xs text-[#71717A] mb-1">{label}</p>
      <p className="text-sm font-mono font-medium text-[#FAFAFA]">
        {payload[0].value.toLocaleString()} calls
      </p>
    </div>
  );
}

function formatXAxisDate(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

export function ApiCallsChart({ data }: ApiCallsChartProps) {
  // Show every 5th label to avoid crowding
  const tickIndices = new Set(
    data
      .map((_, i) => i)
      .filter((i) => i % 5 === 0 || i === data.length - 1)
  );

  return (
    <div
      className="w-full h-56"
      role="img"
      aria-label="API calls over the last 30 days line chart"
    >
      <ResponsiveContainer width="100%" height="100%">
        <LineChart
          data={data}
          margin={{ top: 4, right: 4, left: -16, bottom: 0 }}
        >
          <CartesianGrid
            strokeDasharray="3 3"
            stroke="#27272A"
            vertical={false}
          />
          <XAxis
            dataKey="date"
            tick={{ fill: "#71717A", fontSize: 11, fontFamily: "var(--font-geist-mono)" }}
            tickLine={false}
            axisLine={false}
            tickFormatter={(val, idx) =>
              tickIndices.has(idx) ? formatXAxisDate(val) : ""
            }
            interval={0}
          />
          <YAxis
            tick={{ fill: "#71717A", fontSize: 11, fontFamily: "var(--font-geist-mono)" }}
            tickLine={false}
            axisLine={false}
            tickFormatter={(v: number) =>
              v >= 1000 ? `${(v / 1000).toFixed(1)}k` : String(v)
            }
          />
          <Tooltip
            content={<CustomTooltip />}
            cursor={{ stroke: "#3F3F46", strokeWidth: 1 }}
          />
          <Line
            type="monotone"
            dataKey="calls"
            stroke="#2DD4BF"
            strokeWidth={1.5}
            dot={false}
            activeDot={{
              r: 3,
              fill: "#2DD4BF",
              stroke: "#09090B",
              strokeWidth: 2,
            }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
