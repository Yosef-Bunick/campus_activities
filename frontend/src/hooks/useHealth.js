import { useQuery } from '@tanstack/react-query';
import { apiGet } from '../api';

export function useHealth() {
  return useQuery({
    queryKey: ['health'],
    queryFn: () => apiGet('/health'),
    retry: false,
    refetchInterval: 60000,
  });
}
