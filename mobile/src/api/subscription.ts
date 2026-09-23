import apiClient from "./client";
export type SubscriptionPlan = { id: string; name: string; monthly_price: string | number; annual_price: string | number; student_limit?: number | null; teacher_limit?: number | null; features?: string };
export type SubscriptionStatus = { status: string; student_count: number; student_limit?: number | null; plan?: SubscriptionPlan | null };
export const subscriptionApi = { status: () => apiClient.get<SubscriptionStatus>("/subscription").then((r) => r.data), plans: () => apiClient.get<SubscriptionPlan[]>("/subscription/plans").then((r) => r.data) };
