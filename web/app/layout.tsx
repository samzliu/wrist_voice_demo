import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Coworker",
  description: "Voice AI coworking — edit together in real time",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body style={{ margin: 0, fontFamily: "system-ui, -apple-system, sans-serif" }}>
        {children}
      </body>
    </html>
  );
}
