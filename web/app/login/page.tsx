"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { api } from "@/lib/api";
const schema = z.object({ email: z.string().email(), password: z.string().min(8) }); type Form = z.infer<typeof schema>;
export default function LoginPage() { const router = useRouter(), { register, handleSubmit, formState: { errors, isSubmitting }, setError } = useForm<Form>({ resolver: zodResolver(schema) }); const submit = async (values: Form) => { try { const data = await api<{ access_token: string }>("/auth/login", { method: "POST", body: JSON.stringify(values) }); localStorage.setItem("tuiro.access-token", data.access_token); router.replace("/home"); } catch { setError("root", { message: "We could not sign you in." }); } }; return <main className="mx-auto mt-20 max-w-sm rounded-xl bg-white p-6 shadow dark:bg-slate-900"><h1 className="text-2xl font-semibold">Sign in to Tuiro</h1><form onSubmit={handleSubmit(submit)} className="mt-5 space-y-4"><input {...register("email")} type="email" placeholder="Email" className="w-full rounded border p-3"/><input {...register("password")} type="password" placeholder="Password" className="w-full rounded border p-3"/>{(errors.email || errors.password || errors.root) && <p role="alert" className="text-sm text-red-600">{errors.email?.message ?? errors.password?.message ?? errors.root?.message}</p>}<button disabled={isSubmitting} className="w-full rounded bg-blue-600 p-3 text-white disabled:opacity-50">{isSubmitting ? "Signing in…" : "Sign in"}</button></form><p className="mt-4 text-sm">New here? <Link className="text-blue-600" href="/onboarding">Create an organization</Link></p></main>; }
