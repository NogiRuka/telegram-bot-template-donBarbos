import { useQuery } from '@tanstack/react-query'
import { getUsers, getUser } from '@/lib/api'

interface UseUsersParams {
  page?: number
  per_page?: number
  search?: string
  is_admin?: boolean
  is_block?: boolean
  is_premium?: boolean
  sort_by?: string
  sort_order?: 'asc' | 'desc'
}

export function useUsers(params: UseUsersParams = {}) {
  return useQuery({
    queryKey: ['users', params],
    queryFn: () => getUsers(params),
    staleTime: 5 * 60 * 1000, // 5 minutes
    refetchOnWindowFocus: false,
  })
}

export function useUser(id: number) {
  return useQuery({
    queryKey: ['user', id],
    queryFn: () => getUser(id),
    enabled: !!id,
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}