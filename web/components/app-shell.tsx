"use client";
import Link from "next/link";
import { Bell, CalendarDays, CheckSquare, ChevronDown, Home, Menu, Settings, Users } from "lucide-react";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { ErrorBoundary } from "@/components/error-boundary";
import { useTerm } from "@/components/use-term";

type Me = { display_name: string; role: string; organization_id: string };
const moduleFor: Record<string, string> = { "/home": "home", "/people": "people", "/groups": "groups", "/attendance": "attendance", "/requests": "requests", "/work": "work", "/calendar": "calendar", "/settings": "settings" };

export function AppShell({ children }: { children: React.ReactNode }) {
  const router = useRouter(), pathname = usePathname(), { term } = useTerm();
  const [me, setMe] = useState<Me | null>(null), [modules, setModules] = useState<string[]>([]), [open, setOpen] = useState(false);
  useEffect(() => { api<Me>("/me").then(async (user) => { setMe(user); if (["OWNER", "ADMIN"].includes(user.role)) { const settings = await api<{ enabled_modules: string[] }>("/settings"); setModules(settings.enabled_modules ?? []); } }).catch(() => router.replace("/login")); }, [router]);
  const nav = [
    ["/home", "home", "Home", Home], ["/people", "people", term("person"), Users], ["/groups", "groups", term("group"), Users],
    ["/attendance", "attendance", term("attendance"), CalendarDays], ["/requests", "requests", term("leave_request"), CheckSquare],
    ["/work", "work", term("work_item"), CheckSquare], ["/calendar", "calendar", "Calendar", CalendarDays], ["/settings", "settings", "Settings", Settings],
  ] as const;
  const visible = nav.filter(([path]) => (path !== "/settings" || ["OWNER", "ADMIN"].includes(me?.role ?? "")) && (modules.length === 0 || modules.includes(moduleFor[path])));
  const signOut = () => { localStorage.removeItem("tuiro.access-token"); router.replace("/login"); };
  return <div className="min-h-screen md:grid md:grid-cols-[16rem_1fr]">
    <aside className={`${open ? "block" : "hidden"} fixed inset-y-0 z-20 w-64 border-r border-slate-200 bg-white p-4 md:static md:block dark:border-slate-700 dark:bg-slate-900`}>
      <Link href="/home" className="mb-8 block text-xl font-semibold tracking-tight">Tuiro</Link>
      <nav aria-label="Main navigation" className="space-y-1">{visible.map(([href, , title, Icon]) => <Link key={href} href={href} className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm ${pathname === href ? "bg-blue-600 text-white" : "hover:bg-slate-100 dark:hover:bg-slate-800"}`}><Icon size={18}/>{title}</Link>)}</nav>
    </aside>
    <div className="min-w-0"><header className="flex h-16 items-center justify-between border-b border-slate-200 bg-white px-4 dark:border-slate-700 dark:bg-slate-900"><button aria-label="Toggle menu" className="md:hidden" onClick={() => setOpen(!open)}><Menu /></button><div className="text-sm text-slate-500">{me?.role ?? "Loading…"}</div><div className="flex items-center gap-4"><Link href="/notifications" aria-label="Notifications"><Bell size={19}/></Link><button onClick={signOut} className="flex items-center gap-1 text-sm">{me?.display_name ?? "Account"}<ChevronDown size={15}/></button></div></header><ErrorBoundary><main className="mx-auto max-w-7xl p-4 md:p-8">{children}</main></ErrorBoundary></div>
  </div>;
}
