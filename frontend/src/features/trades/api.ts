// frontend/src/features/trades/api.ts
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import type { CompletedTradeRow } from './types';

export const useCompletedTrades = () => {
  return useQuery({
    queryKey: ['completedTrades'],
    queryFn: async (): Promise<CompletedTradeRow[]> => {
      try {
        const { data } = await axios.get('/api/v1/trades/completed');
        return data?.data ?? [];
      } catch (error) {
        console.warn('Backend endpoint /api/v1/trades/completed not yet active:', error);
        return [];
      }
    },
    staleTime: 5 * 60 * 1000,
  });
};