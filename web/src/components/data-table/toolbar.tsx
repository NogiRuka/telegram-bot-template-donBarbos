import { Cross2Icon } from '@radix-ui/react-icons'
import { type Table } from '@tanstack/react-table'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { DataTableViewOptions } from './view-options'

type DataTableToolbarProps<TData> = {
  table: Table<TData>
  searchPlaceholder?: string
  searchKey?: string
  onSearchBlur?: () => void
  onGlobalFilterChange?: (value: string) => void
  onReset?: () => void
}

export function DataTableToolbar<TData>({
  table,
  searchPlaceholder = 'Filter...',
  searchKey,
  onSearchBlur,
  onGlobalFilterChange,
  onReset,
}: DataTableToolbarProps<TData>) {
  const isFiltered = table.getState().globalFilter

  return (
    <div className='flex items-center justify-between'>
      <div className='flex flex-1 flex-col-reverse items-start gap-y-2 sm:flex-row sm:items-center sm:space-x-2'>
        {searchKey ? (
          <Input
            placeholder={searchPlaceholder}
            value={
              (table.getColumn(searchKey)?.getFilterValue() as string) ?? ''
            }
            onChange={(event) =>
              table.getColumn(searchKey)?.setFilterValue(event.target.value)
            }
            onBlur={onSearchBlur}
            onKeyDown={(event) => {
              if (event.key === 'Enter' && onSearchBlur) {
                onSearchBlur()
              }
            }}
            className='h-8 w-[150px] lg:w-[250px]'
          />
        ) : (
          <Input
            placeholder={searchPlaceholder}
            value={table.getState().globalFilter ?? ''}
            onChange={(event) => table.setGlobalFilter(event.target.value)}
            onBlur={onSearchBlur}
            onKeyDown={(event) => {
              if (event.key === 'Enter' && onSearchBlur) {
                onSearchBlur()
              }
            }}
            className='h-8 w-[150px] lg:w-[250px]'
          />
        )}
        {isFiltered && (
          <Button
            variant='ghost'
            onClick={() => {
              // 清除React Table状态
              table.setGlobalFilter('')
              // 调用专门的重置函数
              if (onReset) {
                onReset()
              } else {
                // 回退方案：清除URL状态管理中的globalFilter
                if (onGlobalFilterChange) {
                  onGlobalFilterChange('')
                }
                // 重置后触发搜索
                if (onSearchBlur) {
                  onSearchBlur()
                }
              }
            }}
            className='h-8 px-2 lg:px-3'
          >
            重置
            <Cross2Icon className='ms-2 h-4 w-4' />
          </Button>
        )}
      </div>
      <DataTableViewOptions table={table} />
    </div>
  )
}
