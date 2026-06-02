import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "IB Desk",
  description: "Ingest research documents into the IB Desk sheet builder.",
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
