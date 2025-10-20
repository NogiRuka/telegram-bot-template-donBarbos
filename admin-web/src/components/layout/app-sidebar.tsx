'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarHeader,
  SidebarFooter,
} from '@/components/ui/sidebar';
import {
  Home,
  Users,
  UserCheck,
  Settings,
  BarChart3,
  Shield,
  LogOut,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';

/**
 * 导航菜单项配置
 */
const navigationItems = [
  {
    title: '仪表板',
    icon: Home,
    href: '/dashboard',
    description: '系统概览和统计数据',
  },
  {
    title: '用户管理',
    icon: Users,
    href: '/users',
    description: 'Telegram 用户管理',
  },
  {
    title: '管理员',
    icon: UserCheck,
    href: '/admins',
    description: '系统管理员管理',
  },
  {
    title: '角色权限',
    icon: Shield,
    href: '/roles',
    description: '角色和权限管理',
  },
  {
    title: '数据统计',
    icon: BarChart3,
    href: '/analytics',
    description: '数据分析和报表',
  },
  {
    title: '系统设置',
    icon: Settings,
    href: '/settings',
    description: '系统配置和设置',
  },
];

/**
 * 应用侧边栏组件
 */
export function AppSidebar() {
  const pathname = usePathname();

  const handleLogout = () => {
    // TODO: 实现登出逻辑
    console.log('Logout clicked');
  };

  return (
    <Sidebar className="border-r">
      <SidebarHeader className="p-4">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <Shield className="h-4 w-4" />
          </div>
          <div className="flex flex-col">
            <span className="text-sm font-semibold">Telegram Bot</span>
            <span className="text-xs text-muted-foreground">管理后台</span>
          </div>
        </div>
      </SidebarHeader>

      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>主要功能</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {navigationItems.map((item) => {
                const isActive = pathname === item.href;
                return (
                  <SidebarMenuItem key={item.href}>
                    <SidebarMenuButton asChild isActive={isActive}>
                      <Link href={item.href} className="flex items-center gap-3">
                        <item.icon className="h-4 w-4" />
                        <span>{item.title}</span>
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                );
              })}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter className="p-4">
        <div className="flex items-center gap-3 mb-3">
          <Avatar className="h-8 w-8">
            <AvatarImage src="/placeholder-avatar.jpg" alt="Admin" />
            <AvatarFallback>AD</AvatarFallback>
          </Avatar>
          <div className="flex flex-col flex-1 min-w-0">
            <span className="text-sm font-medium truncate">管理员</span>
            <span className="text-xs text-muted-foreground truncate">
              admin@example.com
            </span>
          </div>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={handleLogout}
          className="w-full justify-start gap-2"
        >
          <LogOut className="h-4 w-4" />
          退出登录
        </Button>
      </SidebarFooter>
    </Sidebar>
  );
}