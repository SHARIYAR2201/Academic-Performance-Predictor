import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Academic Performance Prediction & Early-Warning System",
  description: "ML-based academic analytics platform",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full flex flex-col font-sans">{children}</body>
    </html>
  );
}
