import { useQuery } from '@tanstack/react-query';
import { apiGet } from '../api';

// The app polls for fresh events every 60 s while open (architecture §2).
// All event lists share the ['events', …] cache so tab switches don't refetch.
export function useEvents(params) {
  const qs = params.toString();
  return useQuery({
    queryKey: ['events', qs],
    queryFn: () => apiGet(`/events?${qs}`),
    refetchInterval: 60000,
  });
}

export function useRooms() {
  return useQuery({ queryKey: ['rooms'], queryFn: () => apiGet('/rooms'), staleTime: 10 * 60000 });
}

export function useMajors() {
  return useQuery({ queryKey: ['majors'], queryFn: () => apiGet('/auth/majors'), staleTime: 60 * 60000 });
}
