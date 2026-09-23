import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { PropsWithChildren, useEffect } from "react";

import { useAuthStore } from "@/store/auth";

const queryClient = new QueryClient({ defaultOptions: { queries: { staleTime: 30000, retry: 1 } } });

export function AppProvider({ children }: PropsWithChildren) {
    const hydrate = useAuthStore((state) => state.hydrate);
    useEffect(() => { void hydrate(); }, [hydrate]);
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}
