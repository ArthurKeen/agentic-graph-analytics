import type { Metadata } from "next";
import "./styles.css";

export const metadata: Metadata = {
  title: "Arango Graph Analytics Workspace",
  description: "Arango workspace for graph analytics workflows"
};

export default function RootLayout({
  children
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
