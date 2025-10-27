import {
  ArrowDownIcon,
  ArrowUpIcon,
  CaretSortIcon,
} from '@radix-ui/react-icons'
import { type Column } from '@tanstack/react-table'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'

type DataTableColumnHeaderProps<TData, TValue> =
  React.HTMLAttributes<HTMLDivElement> & {
    column: Column<TData, TValue>
    title: string
  }

export function DataTableColumnHeader<TData, TValue>({
  column,
  title,
  className,
}: DataTableColumnHeaderProps<TData, TValue>) {
  if (!column.getCanSort()) {
    return <div className={cn(className)}>{title}</div>
  }

  const handleSort = () => {
    const currentSort = column.getIsSorted()
    if (currentSort === false) {
      // 无排序 → 升序
      column.toggleSorting(false)
    } else if (currentSort === 'asc') {
      // 升序 → 降序
      column.toggleSorting(true)
    } else {
      // 降序 → 无排序
      column.clearSorting()
    }
  }

  return (
    <Button
      variant='ghost'
      size='sm'
      className={cn('hover:bg-accent h-8 cursor-pointer', className)}
      onClick={handleSort}
    >
      <span>{title}</span>
      {column.getIsSorted() === 'desc' ? (
        <ArrowDownIcon className='ms-2 h-4 w-4' />
      ) : column.getIsSorted() === 'asc' ? (
        <ArrowUpIcon className='ms-2 h-4 w-4' />
      ) : (
        <CaretSortIcon className='ms-2 h-4 w-4' />
      )}
    </Button>
  )
}
