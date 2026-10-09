"use client";
import { useState } from "react";
import { api } from "@/lib/api";
import { useTerm } from "@/components/use-term";

export default function SettingsPage() {
  const { terms, refetch } = useTerm(); const [state, setState] = useState(""), [saving, setSaving] = useState(false);
  const save = async () => { setSaving(true); setState(""); try { await api("/terminology", { method: "PUT", body: JSON.stringify({ terms }) }); await refetch(); setState("Saved"); } catch { setState("Could not save changes"); } finally { setSaving(false); } };
  return <><h1 className="text-2xl font-semibold">Settings</h1><p className="mt-2 text-slate-500">Change display labels without changing your data model.</p><div className="mt-6 max-w-2xl space-y-3">{Object.entries(terms).map(([key, value]) => <div key={key} className="grid grid-cols-3 items-center gap-3 rounded-lg border border-slate-200 bg-white p-3 dark:border-slate-700 dark:bg-slate-900"><span className="text-sm text-slate-500">{key}</span><input aria-label={`${key} singular`} value={value.singular} onChange={(e) => { terms[key] = { ...value, singular: e.target.value }; refetch(); }} className="rounded border p-2"/><input aria-label={`${key} plural`} value={value.plural} onChange={(e) => { terms[key] = { ...value, plural: e.target.value }; refetch(); }} className="rounded border p-2"/></div>)}</div><button disabled={saving} onClick={save} className="mt-5 rounded bg-blue-600 px-4 py-2 text-white disabled:opacity-50">{saving ? "Saving…" : "Save terminology"}</button>{state && <p role="status" className="mt-3 text-sm">{state}</p>}</>;
}
