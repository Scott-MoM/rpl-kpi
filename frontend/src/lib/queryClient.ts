import { QueryClient } from "@tanstack/react-query";
import { ApiError } from "./api";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60_000,
      refetchOnWindowFocus: false,
      retry: (failureCount, error) => {
        if (!(error instanceof ApiError)) return failureCount < 1;
        if (error.status && error.status >= 400 && error.status < 500 && error.status !== 408 && error.status !== 429) {
          return false;
        }
        return failureCount < 1;
      },
      retryDelay: 1_000
    }
  }
});
