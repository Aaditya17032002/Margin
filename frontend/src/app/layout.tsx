import type { Metadata, Viewport } from "next";
import { Fraunces, Geist, Geist_Mono } from "next/font/google";

import { Providers } from "@/components/providers";
import "./globals.css";

const fraunces = Fraunces({
  subsets: ["latin"],
  variable: "--font-fraunces",
  display: "swap",
  axes: ["SOFT", "WONK", "opsz"],
});

const geist = Geist({
  subsets: ["latin"],
  variable: "--font-geist-sans",
  display: "swap",
});

const geistMono = Geist_Mono({
  subsets: ["latin"],
  variable: "--font-geist-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    default: "Margin — capture intelligence for government solicitations",
    template: "%s · Margin",
  },
  description:
    "Margin reads a solicitation line by line and returns a grounded, citation-backed analysis: what the agency wants, which rules apply, what disqualifies you, and what to ask before the deadline.",
  applicationName: "Margin",
  authors: [{ name: "Margin" }],
  keywords: ["RFP analysis", "compliance matrix", "capture management", "government solicitations"],
  metadataBase: new URL("https://margin.example"),
  openGraph: {
    type: "website",
    siteName: "Margin",
    title: "Margin — capture intelligence for government solicitations",
    description:
      "Every finding carries the page, the section, and the line it stands on. Read the solicitation properly before you commit a team to it.",
  },
  twitter: {
    card: "summary_large_image",
    title: "Margin",
    description: "Citation-backed analysis of government solicitations.",
  },
  robots: { index: true, follow: true },
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#F6F2E9" },
    { media: "(prefers-color-scheme: dark)", color: "#191612" },
  ],
  colorScheme: "light dark",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    // The font variables belong on <html>, not <body>: `@layer base` rules and
    // anything reading them from `:root` resolve against the document element,
    // and a variable defined one level lower is invalid at that point.
    <html
      lang="en"
      data-appearance="paper"
      className={`${fraunces.variable} ${geist.variable} ${geistMono.variable}`}
      suppressHydrationWarning
    >
      <body className="antialiased">
        <a
          href="#main"
          className="sr-only z-100 focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:rounded-md focus:border focus:border-line-strong focus:bg-paper-raised focus:px-4 focus:py-2 focus:text-sm focus:text-ink focus:shadow-[var(--shadow-float)]"
        >
          Skip to content
        </a>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
