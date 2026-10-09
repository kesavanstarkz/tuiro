"use client";
import { FormEvent, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useTerm } from "@/components/use-term";

type Employee = { id: string; employee_number: string; first_name: string; last_name: string; email?: string; status: string };
export default function PeoplePage() {
  const { term } = useTerm(); const [items, setItems] = useState<Employee[]>([]); const [error, setError] = useState(""); const [open, setOpen] = useState(false);
  const load = () => api<Employee[]>("/api/v2/people/employees").then(setItems).catch((e: Error) => setError(e.message));
  useEffect(() => { void load(); }, []);
  async function create(event: FormEvent<HTMLFormElement>) { event.preventDefault(); const data = new FormData(event.currentTarget); setError(""); try { await api("/api/v2/people/employees", { method: "POST", body: JSON.stringify({ employee_number: data.get("number"), first_name: data.get("first_name"), last_name: data.get("last_name"), email: data.get("email") || null }) }); event.currentTarget.reset(); setOpen(false); load(); } catch (e) { setError((e as Error).message); } }
  return <section><div className="flex items-center justify-between gap-4"><div><h1 className="text-2xl font-semibold">{term("person", true)}</h1><p className="mt-1 text-sm text-slate-500">Manage organization member records.</p></div><button className="rounded-lg bg-blue-600 px-3 py-2 text-sm text-white" onClick={() => setOpen(!open)}>Add {term("person", false)}</button></div>
    {open && <form onSubmit={create} className="mt-6 grid gap-3 rounded-xl border p-4 md:grid-cols-2"><input required name="number" placeholder="Employee number" className="rounded border p-2"/><input required name="first_name" placeholder="First name" className="rounded border p-2"/><input name="last_name" placeholder="Last name" className="rounded border p-2"/><input name="email" type="email" placeholder="Email" className="rounded border p-2"/><button className="w-fit rounded bg-blue-600 px-3 py-2 text-sm text-white">Save</button></form>}
    {error && <p role="alert" className="mt-4 text-sm text-red-600">{error}</p>}<div className="mt-6 overflow-x-auto rounded-xl border"><table className="w-full text-left text-sm"><thead className="bg-slate-50 text-slate-500"><tr><th className="p-3">Name</th><th className="p-3">Number</th><th className="p-3">Email</th><th className="p-3">Status</th></tr></thead><tbody>{items.map((item) => <tr key={item.id} className="border-t"><td className="p-3">{item.first_name} {item.last_name}</td><td className="p-3">{item.employee_number}</td><td className="p-3">{item.email ?? "—"}</td><td className="p-3">{item.status}</td></tr>)}{!items.length && <tr><td colSpan={4} className="p-6 text-center text-slate-500">No records yet.</td></tr>}</tbody></table></div></section>;
}
