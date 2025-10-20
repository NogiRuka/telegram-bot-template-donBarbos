'use client';

import { useState } from 'react';
import { usePathname } from 'next/navigation';
import { AppSidebar } from './app-sidebar';
import { AppHeader } from './app-header';
import { SidebarProvider, SidebarInset } from '@/components/ui/sidebar';

interface AppLayoutProps {
  children: React.ReactNode;
}

/**
 * 应用主布局组件
 * 包含侧边栏、头部和主内容区域
 */
export function AppLayout({ children }: AppLayoutProps) {
  const pathname = usePathname();
  
  // 不需要布局的页面（如登录页）
  const noLayoutPages = ['/login', '/register'];
  const shouldShowLayout = !noLayoutPages.includes(pathname);

  if (!shouldShowLayout) {
    return <>{children}</>;
  }

  return (
    <SidebarProvider>
      <div className="flex h-screen w-full">
        <AppSidebar />
        <SidebarInset className="flex flex-col flex-1 overflow-hidden">
          <AppHeader />
          <main className="flex-1 overflow-auto p-6 bg-gray-50/50">
            {children}
          </main>
        </SidebarInset>
      </div>
    </SidebarProvider>
  );
}