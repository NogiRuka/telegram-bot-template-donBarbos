import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { ConfigDrawer } from '@/components/config-drawer'
import { Header } from '@/components/layout/header'
import { Main } from '@/components/layout/main'
import { TopNav } from '@/components/layout/top-nav'
import { ProfileDropdown } from '@/components/profile-dropdown'
import { Search } from '@/components/search'
import { ThemeSwitch } from '@/components/theme-switch'
import { Analytics } from './components/analytics'
import { Overview } from './components/overview'
import { RecentSales } from './components/recent-sales'
import { useQuery } from '@tanstack/react-query'
import { getDashboardStats } from '@/lib/api'
import { Users, UserCheck, UserX, Crown } from 'lucide-react'

export function Dashboard() {
  const { data: stats, isLoading, error } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: getDashboardStats,
  })

  return (
    <>
      {/* ===== Top Heading ===== */}
      <Header>
        <TopNav links={topNav} />
        <div className='ms-auto flex items-center space-x-4'>
          <Search />
          <ThemeSwitch />
          <ConfigDrawer />
          <ProfileDropdown />
        </div>
      </Header>

      {/* ===== Main ===== */}
      <Main>
        <div className='mb-2 flex items-center justify-between space-y-2'>
          <h1 className='text-2xl font-bold tracking-tight'>仪表板</h1>
          <div className='flex items-center space-x-2'>
            <Button>下载</Button>
          </div>
        </div>
        <Tabs
          orientation='vertical'
          defaultValue='overview'
          className='space-y-4'
        >
          <div className='w-full overflow-x-auto pb-2'>
            <TabsList>
              <TabsTrigger value='overview'>概览</TabsTrigger>
              <TabsTrigger value='analytics'>分析</TabsTrigger>
              <TabsTrigger value='reports' disabled>
                报告
              </TabsTrigger>
              <TabsTrigger value='notifications' disabled>
                通知
              </TabsTrigger>
            </TabsList>
          </div>
          <TabsContent value='overview' className='space-y-4'>
            {isLoading ? (
              <div className='grid gap-4 sm:grid-cols-2 lg:grid-cols-4'>
                {[...Array(4)].map((_, i) => (
                  <Card key={i}>
                    <CardHeader className='flex flex-row items-center justify-between space-y-0 pb-2'>
                      <div className='h-4 w-20 bg-gray-200 rounded animate-pulse'></div>
                      <div className='h-4 w-4 bg-gray-200 rounded animate-pulse'></div>
                    </CardHeader>
                    <CardContent>
                      <div className='h-8 w-24 bg-gray-200 rounded animate-pulse mb-2'></div>
                      <div className='h-3 w-32 bg-gray-200 rounded animate-pulse'></div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            ) : error ? (
              <div className='text-center text-red-500 p-4'>
                加载仪表板数据失败: {error.message}
              </div>
            ) : (
              <div className='grid gap-4 sm:grid-cols-2 lg:grid-cols-4'>
                <Card>
                  <CardHeader className='flex flex-row items-center justify-between space-y-0 pb-2'>
                    <CardTitle className='text-sm font-medium'>
                      总用户数
                    </CardTitle>
                    <Users className='text-muted-foreground h-4 w-4' />
                  </CardHeader>
                  <CardContent>
                    <div className='text-2xl font-bold'>{stats?.total_users || 0}</div>
                    <p className='text-muted-foreground text-xs'>
                      注册用户总数
                    </p>
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader className='flex flex-row items-center justify-between space-y-0 pb-2'>
                    <CardTitle className='text-sm font-medium'>
                      今日新用户
                    </CardTitle>
                    <UserCheck className='text-muted-foreground h-4 w-4' />
                  </CardHeader>
                  <CardContent>
                    <div className='text-2xl font-bold'>{stats?.new_users_today || 0}</div>
                    <p className='text-muted-foreground text-xs'>
                      今日加入的用户
                    </p>
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader className='flex flex-row items-center justify-between space-y-0 pb-2'>
                    <CardTitle className='text-sm font-medium'>高级用户</CardTitle>
                    <Crown className='text-muted-foreground h-4 w-4' />
                  </CardHeader>
                  <CardContent>
                    <div className='text-2xl font-bold'>{stats?.premium_users || 0}</div>
                    <p className='text-muted-foreground text-xs'>
                      高级订阅用户
                    </p>
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader className='flex flex-row items-center justify-between space-y-0 pb-2'>
                    <CardTitle className='text-sm font-medium'>
                      被封用户
                    </CardTitle>
                    <UserX className='text-muted-foreground h-4 w-4' />
                  </CardHeader>
                  <CardContent>
                    <div className='text-2xl font-bold'>{stats?.blocked_users || 0}</div>
                    <p className='text-muted-foreground text-xs'>
                      当前被封用户
                    </p>
                  </CardContent>
                </Card>
              </div>
            )}
            <div className='grid grid-cols-1 gap-4 lg:grid-cols-7'>
              <Card className='col-span-1 lg:col-span-4'>
                <CardHeader>
                  <CardTitle>概览</CardTitle>
                </CardHeader>
                <CardContent className='ps-2'>
                  <Overview />
                </CardContent>
              </Card>
              <Card className='col-span-1 lg:col-span-3'>
                <CardHeader>
                  <CardTitle>最近销售</CardTitle>
                  <CardDescription>
                    本月您完成了 265 笔销售。
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <RecentSales />
                </CardContent>
              </Card>
            </div>
          </TabsContent>
          <TabsContent value='analytics' className='space-y-4'>
            <Analytics />
          </TabsContent>
        </Tabs>
      </Main>
    </>
  )
}

const topNav = [
  {
    title: '概览',
    href: 'dashboard/overview',
    isActive: true,
    disabled: false,
  },
  {
    title: '客户',
    href: 'dashboard/customers',
    isActive: false,
    disabled: true,
  },
  {
    title: '产品',
    href: 'dashboard/products',
    isActive: false,
    disabled: true,
  },
  {
    title: '设置',
    href: 'dashboard/settings',
    isActive: false,
    disabled: true,
  },
]
