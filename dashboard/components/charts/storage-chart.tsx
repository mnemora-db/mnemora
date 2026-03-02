"use client";

import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import type { StorageBreakdown } from "@/lib/mock-data";

interface StorageChartProps {
  data: StorageBreakdown[];
}

interface TooltipPayload {
  name: string;
  value: number;
  payload: StorageBreakdown;
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
      <p className="text-xs text-[#A1A1AA] mb-1">{item.name}</p>
      <p className="text-sm font-mono font-medium text-[#FAFAFA]">
        {item.payload.valueGb} GB ({item.payload.percentage}%)
      </p>
    </div>
  );
}

interface LegendPayloadItem {
  value: string;
  color: string;
}

interface CustomLegendProps {
  payload?: LegendPayloadItem[];
}

function CustomLegend({ payload }: CustomLegendProps) {
  if (!payload) return null;
  return (
    <ul className="flex flex-col gap-1.5 mt-2">
      {payload.map((entry) => (
        <li key={entry.value} className="flex items-center gap-2 text-xs">
          <span
            className="w-2.5 h-2.5 rounded-sm shrink-0"
            style={{ backgroundColor: entry.color }}
            aria-hidden="true"
          />
          <span className="text-[#A1A1AA]">{entry.value}</span>
        </li>
      ))}
    </ul>
  );
}

export function StorageChart({ data }: StorageChartProps) {
  return (
    <div
      className="w-full h-56 flex items-center justify-center"
      role="img"
      aria-label="Storage breakdown donut chart"
    >
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={data}
            cx="40%"
            cy="50%"
            innerRadius={52}
            outerRadius={76}
            dataKey="valueGb"
            nameKey="name"
            paddingAngle={2}
            strokeWidth={0}
          >
            {data.map((entry) => (
              <Cell key={entry.name} fill={entry.color} />
            ))}
          </Pie>
          <Tooltip content={<CustomTooltip />} />
          <Legend
            layout="vertical"
            align="right"
            verticalAlign="middle"
            content={<CustomLegend />}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
