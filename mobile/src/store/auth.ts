import { create } from "zustand";

import apiClient, { clearTokens, loadTokens, saveTokens, setRefreshFailureHandler } from "@/api/client";

export type User = { id: string; email: string; display_name: string; organization_id: string; role: string };
export type OrganizationItem = { id: string; name: string; role: string };

export type SignInResult = {
    requiresOrgSelection: boolean;
    organizations: OrganizationItem[];
};

type AuthState = {
    user: User | null;
    hydrated: boolean;
    signIn: (email: string, password: string, organizationId?: string) => Promise<SignInResult>;
    switchOrganization: (organizationId: string) => Promise<void>;
    register: (payload: { email: string; password: string; display_name: string; organization_name: string }) => Promise<void>;
    hydrate: () => Promise<void>;
    signOut: () => Promise<void>;
};

export const useAuthStore = create<AuthState>((set) => ({
    user: null,
    hydrated: false,
    signIn: async (email, password, organizationId) => {
        const payload: { email: string; password: string; organization_id?: string } = { email, password };
        if (organizationId) {
            payload.organization_id = organizationId;
        }
        const { data } = await apiClient.post("/auth/login", payload);
        if (data.organizations && data.organizations.length > 1 && !data.access_token) {
            return { requiresOrgSelection: true, organizations: data.organizations };
        }
        if (data.access_token && data.refresh_token) {
            await saveTokens(data.access_token, data.refresh_token);
            const me = await apiClient.get<User>("/me");
            set({ user: me.data });
        }
        return { requiresOrgSelection: false, organizations: data.organizations || [] };
    },
    switchOrganization: async (organizationId) => {
        const { data } = await apiClient.post("/auth/switch-organization", { organization_id: organizationId });
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
