"use client";
import { useParams } from "next/navigation";
export default function ModulePage() { const params = useParams<{ module: string }>(); return <><h1 className="capitalize text-2xl font-semibold">{params.module}</h1><p className="mt-2 text-slate-500">This module will be delivered with its backend workflow in its dedicated phase.</p></>; }
