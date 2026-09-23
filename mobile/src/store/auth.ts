import { create } from "zustand";

import apiClient, { clearTokens, loadTokens, saveTokens, setRefreshFailureHandler } from "@/api/client";

type User = { id: string; email: string; display_name: string; organization_id: string; role: string };

type AuthState = {
    user: User | null;
    hydrated: boolean;
    signIn: (email: string, password: string) => Promise<void>;
    register: (payload: { email: string; password: string; display_name: string; organization_name: string }) => Promise<void>;
    hydrate: () => Promise<void>;
    signOut: () => Promise<void>;
};

export const useAuthStore = create<AuthState>((set) => ({
    user: null,
    hydrated: false,
    signIn: async (email, password) => {
        const { data } = await apiClient.post("/auth/login", { email, password });
        await saveTokens(data.access_token, data.refresh_token);
        const me = await apiClient.get<User>("/me");
        set({ user: me.data });
    },
    register: async (payload) => {
        const { data } = await apiClient.post("/auth/register", payload);
        await saveTokens(data.access_token, data.refresh_token);
        const me = await apiClient.get<User>("/me");
        set({ user: me.data });
    },
    hydrate: async () => {
        await loadTokens();
        try {
            const { data } = await apiClient.get<User>("/me");
            set({ user: data, hydrated: true });
        } catch {
            await clearTokens();
            set({ user: null, hydrated: true });
        }
    },
    signOut: async () => {
        await clearTokens();
        set({ user: null });
    },
}));

setRefreshFailureHandler(() => {
    void useAuthStore.getState().signOut();
});
