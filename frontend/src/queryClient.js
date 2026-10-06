import { QueryClient } from "@tanstack/react-query";

// One shared client so sign-in, sign-out and expired sessions can wipe cached data.
// Without this, the next person to sign in on the same tab briefly sees the previous
// user's identity, role and data.
export const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 15_000, retry: 1, refetchOnWindowFocus: false } },
});
