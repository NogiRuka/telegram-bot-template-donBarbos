import { type ColumnDef } from '@tanstack/react-table'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Checkbox } from '@/components/ui/checkbox'
import { DataTableColumnHeader } from '@/components/data-table'
import { LongText } from '@/components/long-text'

import { type User } from '../data/schema'
import { DataTableRowActions } from './data-table-row-actions'

export const usersColumns: ColumnDef<User>[] = [
  {
    id: 'select',
    header: ({ table }) => (
      <Checkbox
        checked={
          table.getIsAllPageRowsSelected() ||
          (table.getIsSomePageRowsSelected() && 'indeterminate')
        }
        onCheckedChange={(value) => table.toggleAllPageRowsSelected(!!value)}
        aria-label='Select all'
        className='translate-y-[2px]'
      />
    ),
    meta: {
      title: '选择',
      className: cn('max-md:sticky start-0 z-10 rounded-tl-[inherit]'),
    },
    cell: ({ row }) => (
      <Checkbox
        checked={row.getIsSelected()}
        onCheckedChange={(value) => row.toggleSelected(!!value)}
        aria-label='Select row'
        className='translate-y-[2px]'
      />
    ),
    enableSorting: false,
    enableHiding: true,
  },
  {
    accessorKey: 'username',
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title='用户名' />
    ),
    cell: ({ row }) => (
      <LongText className='max-w-36 ps-3'>{row.getValue('username')}</LongText>
    ),
    meta: {
      title: '用户名',
      className: cn(
        'drop-shadow-[0_1px_2px_rgb(0_0_0_/_0.1)] dark:drop-shadow-[0_1px_2px_rgb(255_255_255_/_0.1)]',
        'ps-0.5 max-md:sticky start-6 @4xl/content:table-cell @4xl/content:drop-shadow-none'
      ),
    },
    enableHiding: false,
  },
  {
    id: 'fullName',
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title='姓名' />
    ),
    cell: ({ row }) => {
      const { first_name, last_name } = row.original
      const fullName = `${first_name || ''} ${last_name || ''}`.trim()
      return <LongText className='max-w-36'>{fullName || '未设置'}</LongText>
    },
    meta: { title: '姓名', className: 'w-36' },
  },
  {
    accessorKey: 'phone_number',
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title='电话号码' />
    ),
    cell: ({ row }) => (
      <div className='w-fit ps-2 text-nowrap'>
        {row.getValue('phone_number') || '未设置'}
      </div>
    ),
    meta: { title: '电话号码' },
    enableSorting: false,
  },
  {
    accessorKey: 'language_code',
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title='语言' />
    ),
    cell: ({ row }) => <div>{row.getValue('language_code') || '未设置'}</div>,
    meta: { title: '语言' },
    enableSorting: false,
  },
  {
    id: 'status',
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title='状态' />
    ),
    cell: ({ row }) => {
      const user = row.original
      let statusText = '正常'
      let badgeColor = 'text-green-600 border-green-600'
      
      if (user.is_block) {
        statusText = '已封禁'
        badgeColor = 'text-red-600 border-red-600'
      } else if (user.is_suspicious) {
        statusText = '可疑'
        badgeColor = 'text-yellow-600 border-yellow-600'
      } else if (user.is_bot) {
        statusText = '机器人'
        badgeColor = 'text-blue-600 border-blue-600'
      }
      
      return (
        <div className='flex space-x-2'>
          <Badge variant='outline' className={cn('capitalize', badgeColor)}>
            {statusText}
          </Badge>
        </div>
      )
    },
    filterFn: (row, _id, value) => {
      if (!row?.original || !Array.isArray(value)) {
        return false
      }
      const user = row.original
      const status = user.is_block ? 'blocked' : user.is_suspicious ? 'suspicious' : user.is_bot ? 'bot' : 'active'
      return value.includes(status)
    },
    enableHiding: false,
    enableSorting: false,
  },
  {
    id: 'userType',
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title='类型' />
    ),
    cell: ({ row }) => {
      const user = row.original
      const isAdmin = user.is_admin
      const isPremium = user.is_premium
      
      let userType = '普通用户'
      let badgeColor = 'text-gray-600 border-gray-600'
      
      if (isAdmin) {
        userType = '管理员'
        badgeColor = 'text-purple-600 border-purple-600'
      } else if (isPremium) {
        userType = '高级用户'
        badgeColor = 'text-gold-600 border-gold-600'
      }
      
      return (
        <div className='flex items-center gap-x-2'>
          <Badge variant='outline' className={cn('capitalize', badgeColor)}>
            {userType}
          </Badge>
        </div>
      )
    },
    filterFn: (row, _id, value) => {
      if (!row?.original || !Array.isArray(value)) {
        return false
      }
      const user = row.original
      const type = user.is_admin ? 'admin' : user.is_premium ? 'premium' : 'normal'
      return value.includes(type)
    },
    enableSorting: false,
    enableHiding: false,
  },
  {
    accessorKey: 'message_count',
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title='消息数' />
    ),
    cell: ({ row }) => <div>{row.getValue('message_count')}</div>,
    meta: { title: '消息数' },
    enableSorting: true,
  },
  {
    id: 'actions',
    cell: DataTableRowActions,
  },
]
