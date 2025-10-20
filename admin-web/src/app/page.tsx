'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Loader2 } from 'lucide-react';

/**
 * 首页组件
 * 自动重定向到仪表板页面
 */
export default function Home() {
  const router = useRouter();

  useEffect(() => {
    // 重定向到仪表板
    router.push('/dashboard');
  }, [router]);

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center">
        <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4" />
        <p className="text-muted-foreground">正在跳转到仪表板...</p>
      </div>
    </div>
  );
}
