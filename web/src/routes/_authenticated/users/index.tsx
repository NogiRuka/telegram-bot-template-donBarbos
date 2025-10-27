import z from 'zod'
import { createFileRoute } from '@tanstack/react-router'
import { Users } from '@/features/users'
import { userTypes } from '@/features/users/data/data'

const usersSearchSchema = z.object({
  page: z.number().optional().catch(1),
  pageSize: z.number().optional().catch(10),
  // Facet filters
  status: z
    .array(
      z.union([
        z.literal('active'),
        z.literal('blocked'),
        z.literal('suspicious'),
        z.literal('bot'),
      ])
    )
    .optional()
    .catch([]),
  userType: z
    .array(z.enum(userTypes.map((r) => r.value as (typeof userTypes)[number]['value'])))
    .optional()
    .catch([]),
  // Global filter for searching across all fields
  filter: z.string().optional().catch(''),
  // Sorting parameters
  sortBy: z.string().optional().catch('created_at'),
  sortOrder: z.enum(['asc', 'desc']).optional().catch('desc'),
})

export const Route = createFileRoute('/_authenticated/users/')({
  validateSearch: usersSearchSchema,
  component: Users,
})
