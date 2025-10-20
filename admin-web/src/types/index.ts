/**
 * 用户相关类型定义
 */
export interface User {
  id: number;
  username?: string;
  first_name?: string;
  last_name?: string;
  language_code?: string;
  is_admin: boolean;
  is_suspicious: boolean;
  is_block: boolean;
  is_premium: boolean;
  created_at: string;
  updated_at?: string;
}

/**
 * 管理员相关类型定义
 */
export interface Admin {
  id: number;
  first_name?: string;
  last_name?: string;
  email: string;
  active: boolean;
  confirmed_at?: string;
  roles?: Role[];
  created_at?: string;
  updated_at?: string;
}

/**
 * 角色相关类型定义
 */
export interface Role {
  id: number;
  name: string;
  description?: string;
}

/**
 * 登录请求类型
 */
export interface LoginRequest {
  email: string;
  password: string;
}

/**
 * 登录响应类型
 */
export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: Admin;
}

/**
 * API 响应基础类型
 */
export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  message?: string;
  error?: string;
}

/**
 * 分页响应类型
 */
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

/**
 * 统计数据类型
 */
export interface DashboardStats {
  total_users: number;
  new_users_today: number;
  total_admins: number;
  active_users: number;
  blocked_users: number;
  premium_users: number;
}

/**
 * 表格列配置类型
 */
export interface TableColumn<T = any> {
  key: keyof T;
  title: string;
  sortable?: boolean;
  filterable?: boolean;
  render?: (value: any, record: T) => React.ReactNode;
}

/**
 * 表格分页配置类型
 */
export interface TablePagination {
  current: number;
  pageSize: number;
  total: number;
  showSizeChanger?: boolean;
  showQuickJumper?: boolean;
}