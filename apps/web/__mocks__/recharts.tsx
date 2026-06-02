// Test stub for recharts.
//
// The real library measures layout via ResizeObserver, which jsdom does not
// provide, so the deterministic UI tests substitute these lightweight stand-ins.
// The sheet's own chart wrapper (the data-chart container) and the Chart/Table
// toggle are what the tests assert; these stubs only need to render their
// children without throwing. Used via vi.mock("recharts") in the component tests.

import type { ReactNode } from "react";

function Passthrough({ children }: { children?: ReactNode }) {
  return <div data-recharts="true">{children}</div>;
}

function Empty() {
  return null;
}

export const ResponsiveContainer = Passthrough;
export const BarChart = Passthrough;
export const LineChart = Passthrough;
export const PieChart = Passthrough;
export const Pie = Passthrough;
export const Bar = Empty;
export const Line = Empty;
export const Cell = Empty;
export const CartesianGrid = Empty;
export const XAxis = Empty;
export const YAxis = Empty;
export const Tooltip = Empty;
