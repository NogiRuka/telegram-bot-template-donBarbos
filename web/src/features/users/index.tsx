import { getRouteApi } from '@tanstack/react-router'
import { ConfigDrawer } from '@/components/config-drawer'
import { Header } from '@/components/layout/header'
import { Main } from '@/components/layout/main'
import { ProfileDropdown } from '@/components/profile-dropdown'
import { Search } from '@/components/search'
import { ThemeSwitch } from '@/components/theme-switch'
import { UsersDialogs } from './components/users-dialogs'
import { UsersPrimaryButtons } from './components/users-primary-buttons'
import { UsersProvider } from './components/users-provider'
import { UsersTable } from './components/users-table'
import { useUsers } from './hooks/use-users'
import { Skeleton } from '@/components/ui/skeleton'
import { Alert, AlertDescription } from '@/components/ui/alert'

const route = getRouteApi('/_authenticated/users/')

export function Users() {
  const search = route.useSearch()
  const navigate = route.useNavigate()
  
  // 从URL搜索参数中提取API参数
  const apiParams = {
    page: search.page || 1,
    per_page: search.pageSize || 10,
    search: search.filter || undefined, // 使用全局过滤器参数
    is_admin: search.userType?.includes('admin') || undefined,
    is_block: search.status?.includes('blocked') || undefined,
    is_suspicious: search.status?.includes('suspicious') || undefined,
    is_bot: search.status?.includes('bot') || undefined,
    is_premium: search.userType?.includes('premium') || undefined,
    sort_by: search.sortBy || 'created_at',
    sort_order: search.sortOrder || 'desc',
  }
  
  const { data: usersResponse, isLoading, error } = useUsers(apiParams)

  return (
    <UsersProvider>
      <Header fixed>
        <Search />
        <div className='ms-auto flex items-center space-x-4'>
          <ThemeSwitch />
          <ConfigDrawer />
          <ProfileDropdown />
        </div>
      </Header>

      <Main className='flex flex-1 flex-col gap-4 sm:gap-6'>
        <div className='flex flex-wrap items-end justify-between gap-2'>
          <div>
            <h2 className='text-2xl font-bold tracking-tight'>用户列表</h2>
            <p className='text-muted-foreground'>
              在这里管理您的用户和他们的角色。
            </p>
          </div>
          <UsersPrimaryButtons />
        </div>
        
        {error && (
          <Alert variant="destructive">
            <AlertDescription>
              加载用户数据失败: {error.message}
            </AlertDescription>
          </Alert>
        )}
        
        {isLoading ? (
          <div className="space-y-4">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-64 w-full" />
          </div>
        ) : (
          <UsersTable 
            data={usersResponse?.items || []} 
            total={usersResponse?.total || 0}
            search={search} 
            navigate={navigate} 
          />
        )}
      </Main>

      <UsersDialogs />
    </UsersProvider>
  )
}
