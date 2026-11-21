import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Healthspan Passport - Biomarker Extraction",
  description: "Extract structured clinical biomarkers from blood test reports",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="p-6 max-w-6xl mx-auto">
        <header className="border-b pb-4 mb-6">
          <h1 className="text-2xl font-bold">Healthspan Passport</h1>
          <p className="text-sm text-gray-600">Lab Report Biomarker Extraction & Validation</p>
        </header>
        <main>{children}</main>
      </body>
    </html>
  );
}
