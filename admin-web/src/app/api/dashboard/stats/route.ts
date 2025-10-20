import { NextRequest, NextResponse } from 'next/server';

/**
 * 获取仪表板统计数据的API端点
 * GET /api/dashboard/stats
 */
export async function GET(request: NextRequest) {
  try {
    // 模拟统计数据
    const stats = {
      total_users: 1250,
      active_users: 890,
      new_users_today: 45,
      total_messages: 15680,
      messages_today: 234,
      bot_uptime: "15天 8小时",
      last_updated: new Date().toISOString(),
      trends: {
        users_growth: 12.5,
        messages_growth: 8.3,
        activity_growth: -2.1
      },
      recent_activity: [
        {
          id: 1,
          type: "user_joined",
          message: "新用户注册",
          timestamp: new Date(Date.now() - 1000 * 60 * 5).toISOString(),
          user: "用户123"
        },
        {
          id: 2,
          type: "message_sent",
          message: "发送消息",
          timestamp: new Date(Date.now() - 1000 * 60 * 15).toISOString(),
          user: "用户456"
        },
        {
          id: 3,
          type: "bot_command",
          message: "执行命令 /start",
          timestamp: new Date(Date.now() - 1000 * 60 * 30).toISOString(),
          user: "用户789"
        }
      ]
    };

    return NextResponse.json(stats);
  } catch (error) {
    console.error('获取仪表板统计数据失败:', error);
    return NextResponse.json(
      { error: '获取统计数据失败' },
      { status: 500 }
    );
  }
}