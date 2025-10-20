'use client';

import { usePathname } from 'next/navigation';
import { SidebarTrigger } from '@/components/ui/sidebar';
import { Separator } from '@/components/ui/separator';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Bell, Search, Settings, User, LogOut } from 'lucide-react';

/**
 * 页面标题映射
 */
const pageTitles: Record<string, string> = {
  '/dashboard': '仪表板',
  '/users': '用户管理',
  '/admins': '管理员管理',
  '/roles': '角色权限',
  '/analytics': '数据统计',
  '/settings': '系统设置',
};

/**
 * 应用头部组件
 */
export function AppHeader() {
  const pathname = usePathname();
  const pageTitle = pageTitles[pathname] || '管理后台';

  const handleLogout = () => {
    // TODO: 实现登出逻辑
    console.log('Logout clicked');
  };

  return (
    <header className="flex h-16 shrink-0 items-center gap-2 border-b bg-background px-4">
      <SidebarTrigger className="-ml-1" />
      <Separator orientation="vertical" className="mr-2 h-4" />
      
      {/* 页面标题 */}
      <div className="flex flex-1 items-center gap-2">
        <h1 className="text-lg font-semibold">{pageTitle}</h1>
        {pathname === '/dashboard' && (
          <Badge variant="secondary" className="text-xs">
            实时数据
          </Badge>
        )}
      </div>

      {/* 右侧操作区 */}
      <div className="flex items-center gap-2">
        {/* 搜索按钮 */}
        <Button variant="ghost" size="icon" className="h-8 w-8">
          <Search className="h-4 w-4" />
          <span className="sr-only">搜索</span>
        </Button>

        {/* 通知按钮 */}
        <Button variant="ghost" size="icon" className="h-8 w-8 relative">
          <Bell className="h-4 w-4" />
          <span className="absolute -top-1 -right-1 h-3 w-3 bg-red-500 rounded-full text-[10px] text-white flex items-center justify-center">
            3
          </span>
          <span className="sr-only">通知</span>
        </Button>

        {/* 用户菜单 */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="relative h-8 w-8 rounded-full">
              <Avatar className="h-8 w-8">
                <AvatarImage src="/placeholder-avatar.svg" alt="Admin" />
                <AvatarFallback>AD</AvatarFallback>
              </Avatar>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent className="w-56" align="end" forceMount>
            <DropdownMenuLabel className="font-normal">
              <div className="flex flex-col space-y-1">
                <p className="text-sm font-medium leading-none">管理员</p>
                <p className="text-xs leading-none text-muted-foreground">
                  admin@example.com
                </p>
              </div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem>
              <User className="mr-2 h-4 w-4" />
              <span>个人资料</span>
            </DropdownMenuItem>
            <DropdownMenuItem>
              <Settings className="mr-2 h-4 w-4" />
              <span>设置</span>
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={handleLogout}>
              <LogOut className="mr-2 h-4 w-4" />
              <span>退出登录</span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}