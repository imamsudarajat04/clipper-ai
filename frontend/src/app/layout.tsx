import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Clipper AI — Auto Highlight Detection",
  description:
    "Automatically detect and export highlight clips from any YouTube video using AI and signal analysis.",
  keywords: ["youtube", "highlight", "clip", "AI", "video", "whisper", "groq"],
  openGraph: {
    title: "Clipper AI",
    description: "Auto highlight detection from YouTube videos",
    type: "website",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="antialiased">{children}</body>
    </html>
  );
}
