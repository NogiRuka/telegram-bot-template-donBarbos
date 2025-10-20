import type { Metadata, Viewport } from "next";
import { Inter } from 'next/font/google';
import "./globals.css";
import { AppLayout } from '@/components/layout/app-layout';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'Telegram Bot 管理后台',
  description: 'Telegram Bot 管理系统 - 基于 Next.js 和 Shadcn UI',
  keywords: ['Telegram', 'Bot', '管理后台', 'Next.js', 'React'],
  authors: [{ name: 'Admin Team' }],
};

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
};

/**
 * 根布局组件
 * 为整个应用提供基础布局和样式
 */
export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN">
      <body className={`${inter.className} antialiased`}>
        <AppLayout>
          {children}
        </AppLayout>
      </body>
    </html>
  );
}
