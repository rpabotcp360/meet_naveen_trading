"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";
import { AuthGuard } from "@/components/AuthGuard";
import { LiveWebSocketProvider } from "@/components/LiveWebSocketProvider";
import { BackendBanner } from "@/components/BackendBanner";

export function Providers({ children }: { children: React.ReactNode }) {
  const [client] = useState(() => new QueryClient());
  return (
    <AuthGuard>
      <QueryClientProvider client={client}>
        <LiveWebSocketProvider>
          <BackendBanner />
          {children}
        </LiveWebSocketProvider>
      </QueryClientProvider>
    </AuthGuard>
  );
}
