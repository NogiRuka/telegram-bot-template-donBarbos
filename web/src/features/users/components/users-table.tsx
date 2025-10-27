import { useEffect, useState } from 'react'
import {
  type SortingState,
  type VisibilityState,
  flexRender,
  getCoreRowModel,
  getFacetedRowModel,
  getFacetedUniqueValues,
  useReactTable,
} from '@tanstack/react-table'

import { cn } from '@/lib/utils'
import { type NavigateFn, useTableUrlState } from '@/hooks/use-table-url-state'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { DataTablePagination, DataTableToolbar } from '@/components/data-table'
import { type User } from '../data/schema'
import { DataTableBulkActions } from './data-table-bulk-actions'
import { usersColumns as columns } from './users-columns'

type DataTableProps = {
  data: User[]
  total?: number
  search: Record<string, unknown>
  navigate: NavigateFn
}

export function UsersTable({ data, total = 0, search, navigate }: DataTableProps) {
  // Local UI-only states
  const [rowSelection, setRowSelection] = useState({})
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({})
  const [sorting, setSorting] = useState<SortingState>([
    { id: (search.sortBy as string) || 'created_at', desc: ((search.sortOrder as string) || 'desc') === 'desc' }
  ])

  // Local state management for table (uncomment to use local-only state, not synced with URL)
  // const [columnFilters, onColumnFiltersChange] = useState<ColumnFiltersState>([])
  // const [pagination, onPaginationChange] = useState<PaginationState>({ pageIndex: 0, pageSize: 10 })

  // Synced with URL states (keys/defaults mirror users route search schema)
  const {
    globalFilter,
    onGlobalFilterChange,
    triggerGlobalFilterSearch,
    columnFilters,
    onColumnFiltersChange,
    pagination,
    onPaginationChange,
    ensurePageInRange,
  } = useTableUrlState({
    search,
    navigate,
    pagination: { defaultPage: 1, defaultPageSize: 10 },
    globalFilter: { enabled: true, key: 'filter' },
    columnFilters: [
      { columnId: 'status', searchKey: 'status', type: 'array' },
      { columnId: 'userType', searchKey: 'userType', type: 'array' },
    ],
  })

  // Calculate total pages for server-side pagination
  const pageCount = Math.ceil(total / pagination.pageSize)

  // eslint-disable-next-line react-hooks/incompatible-library
  const table = useReactTable({
    data,
    columns,
    pageCount, // Set the total page count for server-side pagination
    state: {
      sorting,
      pagination,
      rowSelection,
      columnFilters,
      columnVisibility,
      globalFilter,
    },
    enableRowSelection: true,
    manualPagination: true, // Enable server-side pagination
    manualSorting: true, // Enable server-side sorting
    manualFiltering: true, // Enable server-side filtering
    onPaginationChange,
    onColumnFiltersChange,
    onGlobalFilterChange,
    onRowSelectionChange: setRowSelection,
    onSortingChange: (updater: any) => {
      const newSorting = typeof updater === 'function' ? updater(sorting) : updater
      setSorting(newSorting)
      
      // Update URL with new sorting parameters
      if (newSorting.length > 0) {
        const sortColumn = newSorting[0]
        navigate({
          search: (prev) => ({
            ...prev,
            sortBy: sortColumn.id,
            sortOrder: sortColumn.desc ? 'desc' : 'asc',
            page: 1, // Reset to first page when sorting changes
          }),
        })
      }
    },
    onColumnVisibilityChange: setColumnVisibility,
    getCoreRowModel: getCoreRowModel(),
    // Remove client-side sorting since we're using server-side sorting
    // getSortedRowModel: getSortedRowModel(),
    // Remove client-side pagination models since we're using server-side pagination
    // getPaginationRowModel: getPaginationRowModel(),
    // getFilteredRowModel: getFilteredRowModel(),
    getFacetedRowModel: getFacetedRowModel(),
    getFacetedUniqueValues: getFacetedUniqueValues(),
  })

  useEffect(() => {
    ensurePageInRange(pageCount)
  }, [pageCount, ensurePageInRange])

  // 专门的重置函数，直接清除URL参数
  const handleReset = () => {
    // 清除全局过滤器状态
    if (onGlobalFilterChange) {
      onGlobalFilterChange('')
    }
    // 直接更新URL，清除filter参数
    navigate({
      search: (prev) => ({
        ...prev,
        filter: undefined, // 清除filter参数
        page: undefined,   // 重置到第一页
      }),
    })
  }

  return (
    <div
      className={cn(
        'max-sm:has-[div[role="toolbar"]]:mb-16', // Add margin bottom to the table on mobile when the toolbar is visible
        'flex flex-1 flex-col gap-4'
      )}
    >
      <DataTableToolbar
        table={table}
        searchPlaceholder='搜索用户名、姓名...'
        onSearchBlur={triggerGlobalFilterSearch}
        onGlobalFilterChange={onGlobalFilterChange}
        onReset={handleReset}
      />
      <div className='overflow-hidden rounded-md border'>
        <Table>
          <TableHeader className='bg-muted/30'>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id} className='group/row border-b-2 border-border hover:bg-muted/50'>
                {headerGroup.headers.map((header) => {
                  return (
                    <TableHead
                      key={header.id}
                      colSpan={header.colSpan}
                      className={cn(
                        'bg-muted/30 font-semibold text-foreground/90 h-12 px-4',
                        'border-r border-border/50 last:border-r-0',
                        'group-hover/row:bg-muted/60',
                        header.column.columnDef.meta?.className,
                        header.column.columnDef.meta?.thClassName
                      )}
                    >
                      {header.isPlaceholder
                        ? null
                        : flexRender(
                            header.column.columnDef.header,
                            header.getContext()
                          )}
                    </TableHead>
                  )
                })}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {table.getRowModel().rows?.length ? (
              table.getRowModel().rows.map((row) => (
                <TableRow
                  key={row.id}
                  data-state={row.getIsSelected() && 'selected'}
                  className='group/row hover:bg-muted/30 data-[state=selected]:bg-muted/50'
                >
                  {row.getVisibleCells().map((cell) => (
                    <TableCell
                      key={cell.id}
                      className={cn(
                        'bg-background px-4 py-3',
                        'border-r border-border/30 last:border-r-0',
                        'group-hover/row:bg-muted/30 group-data-[state=selected]/row:bg-muted/50',
                        cell.column.columnDef.meta?.className,
                        cell.column.columnDef.meta?.tdClassName
                      )}
                    >
                      {flexRender(
                        cell.column.columnDef.cell,
                        cell.getContext()
                      )}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell
                  colSpan={columns.length}
                  className='h-24 text-center'
                >
                  暂无数据
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
      <DataTablePagination table={table} total={total} className='mt-auto' />
      <DataTableBulkActions table={table} />
    </div>
  )
}
