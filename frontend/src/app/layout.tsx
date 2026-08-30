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
      <head>
        {/* Apply the stored theme before first paint so a dark-mode user does
            not get a white flash while React hydrates. Light is the default,
            and :root already carries the light palette, so no attribute is
            needed for it. */}
        <script
          dangerouslySetInnerHTML={{
            __html:
              "(function(){try{var t=localStorage.getItem('aga-theme');" +
              "if(t==='dark'||t==='light'){" +
              "document.documentElement.setAttribute('data-theme',t);}}catch(e){}})();"
          }}
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
