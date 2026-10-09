import "./globals.css";
import { Providers } from "@/components/providers";

export const metadata = { title: "Tuiro", description: "Organization management and collaboration" };

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body><Providers>{children}</Providers></body></html>;
}
