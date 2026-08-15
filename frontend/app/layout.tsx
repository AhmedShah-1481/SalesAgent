import type { Metadata } from "next";
import { Inter, Space_Grotesk } from "next/font/google";
import Link from "next/link";
import { Bot } from "lucide-react";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter", display: "swap" });
const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-space-grotesk",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Autonomous AI Sales Agent",
  description:
    "An autonomous agent that discovers, researches, qualifies, and engages leads end-to-end.",
};

const NAV = [
  { href: "/", label: "Overview" },
  { href: "/pipeline", label: "Pipeline" },
  { href: "/knowledge", label: "Knowledge" },
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`dark ${inter.variable} ${spaceGrotesk.variable}`}>
      <body className="min-h-screen antialiased">
        <header className="sticky top-0 z-40 border-b border-border/80 bg-background/70 backdrop-blur-xl">
          <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-6">
            <Link href="/" className="flex items-center gap-2.5">
              <span className="flex size-9 items-center justify-center rounded-lg bg-primary/15 ring-1 ring-primary/30">
                <Bot className="size-5 text-primary" />
              </span>
              <span className="font-[family-name:var(--font-display)] text-lg font-semibold tracking-tight">
                Sales<span className="text-primary">Agent</span>
              </span>
            </Link>
            <nav className="flex items-center gap-1 text-sm">
              {NAV.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className="rounded-md px-3 py-2 text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
                >
                  {item.label}
                </Link>
              ))}
            </nav>
          </div>
        </header>
        <main className="mx-auto max-w-7xl px-6 py-10">{children}</main>
      </body>
    </html>
  );
}
