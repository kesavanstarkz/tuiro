"use client";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { fallbackTerms, label, type Terms } from "@/lib/terms";

export function useTerm() {
  const query = useQuery({ queryKey: ["terminology"], queryFn: () => api<{ terms: Terms }>("/terminology"), staleTime: 60_000 });
  const terms = query.data?.terms ?? fallbackTerms;
  return { term: (key: string, plural = true) => label(terms, key, plural), terms, ...query };
}
