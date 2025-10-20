'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { 
  Users, 
  UserCheck, 
  ShoppingCart, 
  TrendingUp, 
  Activity,
  RefreshCw,
  Calendar,
  BarChart3
} from 'lucide-react';
import { getDashboardStats } from '@/lib/api';
import { DashboardStats } from '@/types';

/**
 * 统计卡片组件
 */
interface StatCardProps {
  title: string;
  value: string | number;
  description?: string;
  icon: React.ReactNode;
  trend?: {
    value: number;
    isPositive: boolean;
  };
}

function StatCard({ title, value, description, icon, trend }: StatCardProps) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        <div className="h-4 w-4 text-muted-foreground">
          {icon}
        </div>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        {description && (
          <p className="text-xs text-muted-foreground">{description}</p>
        )}
        {trend && (
          <div className="flex items-center pt-1">
            <Badge 
              variant={trend.isPositive ? "default" : "destructive"}
              className="text-xs"
            >
              {trend.isPositive ? '+' : ''}{trend.value}%
            </Badge>
            <span className="text-xs text-muted-foreground ml-2">
              相比上月
            </span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

/**
 * 仪表板页面组件
 */
export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date());

  /**
   * 获取仪表板统计数据
   */
  const fetchStats = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const data = await getDashboardStats();
      setStats(data);
      setLastUpdated(new Date());
    } catch (err: any) {
      setError(err.message || '获取统计数据失败');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
  }, []);

  if (error) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">仪表板</h1>
          <p className="text-muted-foreground">
            系统概览和关键指标
          </p>
        </div>
        
        <Alert variant="destructive">
          <AlertDescription>
            {error}
            <Button 
              variant="outline" 
              size="sm" 
              className="ml-4"
              onClick={fetchStats}
            >
              重试
            </Button>
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* 页面头部 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">仪表板</h1>
          <p className="text-muted-foreground">
            系统概览和关键指标
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <div className="text-sm text-muted-foreground flex items-center">
            <Calendar className="h-4 w-4 mr-1" />
            最后更新: {lastUpdated.toLocaleTimeString()}
          </div>
          <Button 
            variant="outline" 
            size="sm"
            onClick={fetchStats}
            disabled={isLoading}
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
            刷新
          </Button>
        </div>
      </div>

      {/* 统计卡片网格 */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="总用户数"
          value={stats?.total_users || 0}
          description="注册用户总数"
          icon={<Users />}
          trend={{
            value: 12,
            isPositive: true
          }}
        />
        
        <StatCard
          title="活跃用户"
          value={stats?.active_users || 0}
          description="本月活跃用户"
          icon={<UserCheck />}
          trend={{
            value: 8,
            isPositive: true
          }}
        />
        
        <StatCard
          title="今日新增用户"
          value={stats?.new_users_today || 0}
          description="今日新增用户"
          icon={<TrendingUp />}
          trend={{
            value: 15,
            isPositive: true
          }}
        />
        
        <StatCard
          title="管理员总数"
          value={stats?.total_admins || 0}
          description="系统管理员数量"
          icon={<ShoppingCart />}
          trend={{
            value: 5,
            isPositive: true
          }}
        />
      </div>

      {/* 详细信息卡片 */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {/* 系统状态 */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <Activity className="h-5 w-5 mr-2" />
              系统状态
            </CardTitle>
            <CardDescription>
              当前系统运行状态
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm">API 服务</span>
              <Badge variant="default">正常</Badge>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm">数据库</span>
              <Badge variant="default">正常</Badge>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm">Telegram Bot</span>
              <Badge variant="default">运行中</Badge>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm">缓存服务</span>
              <Badge variant="secondary">维护中</Badge>
            </div>
          </CardContent>
        </Card>

        {/* 最近活动 */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <BarChart3 className="h-5 w-5 mr-2" />
              最近活动
            </CardTitle>
            <CardDescription>
              系统最新动态
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="text-sm">
              <div className="font-medium">新用户注册</div>
              <div className="text-muted-foreground">5分钟前</div>
            </div>
            <div className="text-sm">
              <div className="font-medium">管理员登录</div>
              <div className="text-muted-foreground">15分钟前</div>
            </div>
            <div className="text-sm">
              <div className="font-medium">数据备份完成</div>
              <div className="text-muted-foreground">1小时前</div>
            </div>
            <div className="text-sm">
              <div className="font-medium">系统更新</div>
              <div className="text-muted-foreground">3小时前</div>
            </div>
          </CardContent>
        </Card>

        {/* 快速操作 */}
        <Card>
          <CardHeader>
            <CardTitle>快速操作</CardTitle>
            <CardDescription>
              常用管理功能
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            <Button variant="outline" className="w-full justify-start">
              <Users className="h-4 w-4 mr-2" />
              用户管理
            </Button>
            <Button variant="outline" className="w-full justify-start">
              <UserCheck className="h-4 w-4 mr-2" />
              管理员设置
            </Button>
            <Button variant="outline" className="w-full justify-start">
              <BarChart3 className="h-4 w-4 mr-2" />
              数据报告
            </Button>
            <Button variant="outline" className="w-full justify-start">
              <Activity className="h-4 w-4 mr-2" />
              系统监控
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* 图表区域（预留） */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>用户增长趋势</CardTitle>
            <CardDescription>
              最近30天用户注册趋势
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-[200px] flex items-center justify-center text-muted-foreground">
              图表组件将在后续版本中实现
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>活跃度分析</CardTitle>
            <CardDescription>
              用户活跃度统计
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-[200px] flex items-center justify-center text-muted-foreground">
              图表组件将在后续版本中实现
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}