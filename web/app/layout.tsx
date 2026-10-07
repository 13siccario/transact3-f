import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "transact3 cost anatomy",
  description: "What it costs to send money into India by bank, stablecoin or onshore exchange. Research findings, not advice.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
