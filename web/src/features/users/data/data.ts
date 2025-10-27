import { Shield, UserCheck, Users, Bot } from 'lucide-react'
import { type UserStatus } from './schema'

export const callTypes = new Map<UserStatus, string>([
  ['active', 'bg-teal-100/30 text-teal-900 dark:text-teal-200 border-teal-200'],
  ['inactive', 'bg-neutral-300/40 border-neutral-300'],
  ['blocked', 'bg-destructive/10 dark:bg-destructive/50 text-destructive dark:text-primary border-destructive/10'],
  [
    'suspended',
    'bg-destructive/10 dark:bg-destructive/50 text-destructive dark:text-primary border-destructive/10',
  ],
])

// 用户状态选项（用于筛选）
export const userStatuses = [
  {
    label: '正常',
    value: 'active',
    icon: UserCheck,
    color: '#10b981', // emerald-500
  },
  {
    label: '已封禁',
    value: 'blocked',
    icon: Shield,
    color: '#ef4444', // red-500
  },
  {
    label: '可疑',
    value: 'suspicious',
    icon: Users,
    color: '#f59e0b', // amber-500
  },
  {
    label: '机器人',
    value: 'bot',
    icon: Bot,
    color: '#8b5cf6', // violet-500
  },
] as const

// 用户类型选项（用于筛选）
export const userTypes = [
  {
    label: '普通用户',
    value: 'normal',
    icon: Users,
    color: '#6b7280', // gray-500
  },
  {
    label: '高级用户',
    value: 'premium',
    icon: UserCheck,
    color: '#3b82f6', // blue-500
  },
  {
    label: '管理员',
    value: 'admin',
    icon: Shield,
    color: '#dc2626', // red-600
  },
] as const
