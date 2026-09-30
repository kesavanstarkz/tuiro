import apiClient from "./client";
export type CentreSettings = { id: string; name: string; country_code: string; currency_code: string; timezone: string; locale: string };
export const settingsApi = { get: () => apiClient.get<CentreSettings>("/settings").then((r) => r.data), update: (payload: Partial<Pick<CentreSettings, "name" | "country_code" | "currency_code" | "timezone" | "locale">>) => apiClient.patch<CentreSettings>("/settings", payload).then((r) => r.data) };
