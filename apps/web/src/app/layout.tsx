import type { Metadata } from "next";
import "./globals.css";
import { Geist, Geist_Mono, Syne } from "next/font/google";
import { cn } from "@/lib/utils";

const geist = Geist({ subsets: ["latin"], variable: "--font-sans" });
const geistMono = Geist_Mono({ subsets: ["latin"], variable: "--font-mono" });
const syne = Syne({
  subsets: ["latin"],
  variable: "--font-display",
  weight: ["400", "500", "600", "700", "800"],
});

export const metadata: Metadata = {
  title: "findme",
  description: "AI-powered visibility platform",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={cn(geist.variable, geistMono.variable, syne.variable)}>
      <body className="bg-background text-foreground antialiased">{children}</body>
    </html>
  );
}
