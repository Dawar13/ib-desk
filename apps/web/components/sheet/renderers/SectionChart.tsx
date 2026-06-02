"use client";

// Chart renderer for chart-hinted sections, driven by recharts. It draws what the
// engine's render hint says (a bar or line timeseries, or a breakdown pie) from
// already-validated chart data. It does not re-decide whether a chart is
// warranted: the typing pass enforced that and the parent enforces the safe
// fallback to a table. Clicking a bar or slice opens that value's evidence; the
// table view (one toggle away) is the guaranteed path to evidence on every value.

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell as PieSlice,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { SectionWithCells } from "@ib-desk/shared";
import { categoryAccent } from "@/lib/sheet/category";
import type { ChartData, ChartPoint } from "@/lib/sheet/chart";
import type { EvidenceHandler } from "../types";

const SLICE_PALETTE = [
  "#8c6b4f",
  "#4f6d8c",
  "#5d7d57",
  "#8c5f6f",
  "#6f5d9c",
  "#9c7a3c",
  "#3f7d7a",
  "#9c5a4a",
];

const compact = new Intl.NumberFormat("en", {
  notation: "compact",
  maximumFractionDigits: 1,
});

interface SectionChartProps {
  data: ChartData;
  section: SectionWithCells;
  onEvidence: EvidenceHandler;
}

export default function SectionChart({
  data,
  section,
  onEvidence,
}: SectionChartProps) {
  const accent = categoryAccent(section.category);

  // recharts hands the datum to onClick. Bars and pie slices receive the datum
  // (which carries the originating cell) at the top level; a line's active dot
  // receives it nested under payload. Read both shapes so a click on any chart
  // mark opens its evidence.
  const open = (entry: unknown): void => {
    const node = entry as
      | (Partial<ChartPoint> & { payload?: Partial<ChartPoint> })
      | null;
    const cell = node?.cell ?? node?.payload?.cell;
    if (cell) {
      onEvidence({ cell, section });
    }
  };

  if (data.kind === "breakdown") {
    return (
      <div data-chart="breakdown_pie" className="h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Tooltip />
            <Pie
              data={data.points}
              dataKey="value"
              nameKey="label"
              outerRadius={90}
              onClick={open}
            >
              {data.points.map((point, index) => (
                <PieSlice
                  key={`${point.label}-${index}`}
                  fill={SLICE_PALETTE[index % SLICE_PALETTE.length]}
                />
              ))}
            </Pie>
          </PieChart>
        </ResponsiveContainer>
      </div>
    );
  }

  const isBar = data.variant === "bar";
  return (
    <div
      data-chart={isBar ? "timeseries_bar" : "timeseries_line"}
      className="h-64 w-full"
    >
      <ResponsiveContainer width="100%" height="100%">
        {isBar ? (
          <BarChart data={data.points}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e6ddcc" vertical={false} />
            <XAxis dataKey="label" tick={{ fontSize: 12, fill: "#6c6456" }} />
            <YAxis
              width={56}
              tick={{ fontSize: 12, fill: "#6c6456" }}
              tickFormatter={(value: number) => compact.format(value)}
            />
            <Tooltip />
            <Bar dataKey="value" fill={accent} radius={[3, 3, 0, 0]} onClick={open} />
          </BarChart>
        ) : (
          <LineChart data={data.points}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e6ddcc" vertical={false} />
            <XAxis dataKey="label" tick={{ fontSize: 12, fill: "#6c6456" }} />
            <YAxis
              width={56}
              tick={{ fontSize: 12, fill: "#6c6456" }}
              tickFormatter={(value: number) => compact.format(value)}
            />
            <Tooltip />
            <Line
              type="monotone"
              dataKey="value"
              stroke={accent}
              strokeWidth={2}
              dot={{ r: 3, fill: accent }}
              activeDot={{ r: 5, onClick: open }}
            />
          </LineChart>
        )}
      </ResponsiveContainer>
    </div>
  );
}
