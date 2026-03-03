import type { Metadata } from "next";
import localFont from "next/font/local";
import { SessionProvider } from "@/components/auth/session-provider";
import { Toaster } from "sonner";
import "./globals.css";

const geistSans = localFont({
  src: "./fonts/GeistVF.woff",
  variable: "--font-geist-sans",
  weight: "100 900",
});

const geistMono = localFont({
  src: "./fonts/GeistMonoVF.woff",
  variable: "--font-geist-mono",
  weight: "100 900",
});

export const metadata: Metadata = {
  title: "Mnemora — Memory Infrastructure for AI Agents",
  description:
    "Open-source, serverless memory database for AI agents. 4 memory types, one API, AWS-native. Sub-10ms state reads, vector search, episodic logs.",
  metadataBase: new URL("https://mnemora.dev"),
  openGraph: {
    title: "Mnemora — Memory Infrastructure for AI Agents",
    description:
      "Open-source, serverless memory database for AI agents. 4 memory types, one API, AWS-native.",
    url: "https://mnemora.dev",
    siteName: "Mnemora",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Mnemora — Memory Infrastructure for AI Agents",
    description:
      "Open-source, serverless memory database for AI agents. 4 memory types, one API, AWS-native.",
  },
  icons: { icon: "/icon.svg" },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased bg-[#09090B] text-[#FAFAFA] font-sans`}
      >
        <SessionProvider>{children}</SessionProvider>
        <Toaster
          theme="dark"
          position="bottom-right"
          toastOptions={{
            style: {
              background: "#18181B",
              border: "1px solid #27272A",
              color: "#FAFAFA",
            },
          }}
        />
      </body>
    </html>
  );
}
