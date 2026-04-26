import type { Metadata } from "next";
import { Inter, JetBrains_Mono, Source_Serif_4 } from "next/font/google";
import "./globals.css";
import { ThemeProvider } from "@/lib/theme";
import { ReviewSessionProvider } from "@/lib/reviewSession";
import Nav from "@/components/shell/Nav";
import Statusbar from "@/components/shell/Statusbar";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
});

const sourceSerif = Source_Serif_4({
  variable: "--font-serif",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  style: ["normal", "italic"],
});

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-mono-jb",
  subsets: ["latin"],
  weight: ["400", "500", "600"],
});

export const metadata: Metadata = {
  title: "ResumeRoast — drop a draft, get a roast",
  description:
    "Roast your résumé against 100+ recruiter-tested patterns. ATS-safe rewrites, clean LaTeX, one-page PDF.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" data-theme="dusk" className={`${inter.variable} ${sourceSerif.variable} ${jetbrainsMono.variable}`}>
      <body>
        <ThemeProvider>
          <ReviewSessionProvider>
            <div className="app">
              <Nav />
              {children}
              <Statusbar />
            </div>
          </ReviewSessionProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
