import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "IB Desk",
  description: "Phase 0 wiring proof for the IB Desk research sheet builder.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
