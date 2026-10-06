import { useEffect, useState } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { paged } from "../api.js";

// Fetches one server page and tracks page/pageSize state.
// Changing the page size or the path (filters) resets to page 1.
// Previous rows stay visible while the next page loads.
export default function usePaged(key, path, initialSize = 25) {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSizeState] = useState(initialSize);

  useEffect(() => { setPage(1); }, [path]);

  const q = useQuery({
    queryKey: [key, "paged", path, page, pageSize],
    queryFn: () => paged(path, page, pageSize),
    placeholderData: keepPreviousData,
  });

  const setPageSize = (n) => { setPageSizeState(n); setPage(1); };
  const rows = q.data?.results || [];
  const count = q.data?.count || 0;

  // If rows were deleted and the current page no longer exists, step back.
  const lastPage = Math.max(1, Math.ceil(count / pageSize));
  useEffect(() => { if (q.data && page > lastPage) setPage(lastPage); }, [q.data, page, lastPage]);

  return { rows, count, page, pageSize, setPage, setPageSize, isLoading: q.isLoading, isFetching: q.isFetching, error: q.error };
}
