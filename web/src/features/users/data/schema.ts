import { z } from 'zod'

// 用户状态基于数据库字段定义
const userStatusSchema = z.union([
  z.literal('active'),
  z.literal('inactive'),
  z.literal('blocked'),
  z.literal('suspended'),
])
export type UserStatus = z.infer<typeof userStatusSchema>

// 基于后端API响应的用户数据结构
const userSchema = z.object({
  id: z.number(),
  username: z.string().optional(),
  first_name: z.string().optional(),
  last_name: z.string().optional(),
  phone_number: z.string().optional(),
  bio: z.string().optional(),
  language_code: z.string().optional(),
  last_activity_at: z.string().optional(),
  is_admin: z.boolean(),
  is_suspicious: z.boolean(),
  is_block: z.boolean(),
  is_premium: z.boolean(),
  is_bot: z.boolean(),
  message_count: z.number(),
  created_at: z.string(),
  updated_at: z.string().optional(),
  created_by: z.number().optional(),
  updated_by: z.number().optional(),
})
export type User = z.infer<typeof userSchema>

export const userListSchema = z.array(userSchema)
