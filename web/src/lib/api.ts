import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios';
import { getCookie, setCookie, removeCookie } from '@/lib/cookies';

// 类型定义
export interface User {
  id: number;
  username?: string;
  first_name?: string;
  last_name?: string;
  phone_number?: string;
  bio?: string;
  language_code?: string;
  last_activity_at?: string;
  is_admin: boolean;
  is_suspicious: boolean;
  is_block: boolean;
  is_premium: boolean;
  is_bot: boolean;
  message_count: number;
  created_at: string;
  updated_at?: string;
  created_by?: number;
  updated_by?: number;
}

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

export interface Role {
  id: number;
  name: string;
  description?: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: Admin;
}

export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  message?: string;
  error?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export interface DashboardStats {
  total_users: number;
  new_users_today: number;
  total_admins: number;
  active_users: number;
  blocked_users: number;
  premium_users: number;
}

/**
 * API 客户端类
 * 负责与后端 API 的通信
 */
class ApiClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: import.meta.env.VITE_API_URL || '/api',
      timeout: 10000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // 请求拦截器 - 添加认证 token
    this.client.interceptors.request.use(
      (config) => {
        const token = this.getToken();
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // 响应拦截器 - 处理错误
    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          this.removeToken();
          window.location.href = '/login';
        }
        return Promise.reject(error);
      }
    );
  }

  /**
   * 获取存储的认证 token
   */
  private getToken(): string | null {
    if (typeof window !== 'undefined') {
      return getCookie('auth_token') || null;
    }
    return null;
  }

  /**
   * 设置认证 token
   */
  private setToken(token: string): void {
    if (typeof window !== 'undefined') {
      setCookie('auth_token', token);
    }
  }

  /**
   * 移除认证 token
   */
  private removeToken(): void {
    if (typeof window !== 'undefined') {
      removeCookie('auth_token');
    }
  }

  /**
   * 通用请求方法
   */
  private async request<T>(config: AxiosRequestConfig): Promise<T> {
    try {
      const response: AxiosResponse<T> = await this.client.request(config);
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.message || error.message || '请求失败');
    }
  }

  // ==================== 认证相关 API ====================

  /**
   * 用户登录
   */
  async login(credentials: LoginRequest): Promise<LoginResponse> {
    const response = await this.request<LoginResponse>({
      method: 'POST',
      url: '/auth/login',
      data: credentials,
    });
    
    if (response.access_token) {
      this.setToken(response.access_token);
    }
    
    return response;
  }

  /**
   * 用户登出
   */
  async logout(): Promise<void> {
    try {
      await this.request({
        method: 'POST',
        url: '/auth/logout',
      });
    } finally {
      this.removeToken();
    }
  }

  /**
   * 获取当前用户信息
   */
  async getCurrentUser(): Promise<Admin> {
    return this.request<Admin>({
      method: 'GET',
      url: '/auth/me',
    });
  }

  // ==================== 仪表板相关 API ====================

  /**
   * 获取仪表板统计数据
   */
  async getDashboardStats(): Promise<DashboardStats> {
    return this.request<DashboardStats>({
      method: 'GET',
      url: '/dashboard/stats',
    });
  }

  // ==================== 管理员相关 API ====================

  /**
   * 获取管理员列表
   */
  async getAdmins(params?: {
    page?: number;
    per_page?: number;
    search?: string;
    sort_by?: string;
    sort_order?: 'asc' | 'desc';
  }): Promise<PaginatedResponse<Admin>> {
    return this.request<PaginatedResponse<Admin>>({
      method: 'GET',
      url: '/admins',
      params,
    });
  }

  /**
   * 获取单个管理员信息
   */
  async getAdmin(id: number): Promise<Admin> {
    return this.request<Admin>({
      method: 'GET',
      url: `/admins/${id}`,
    });
  }

  /**
   * 创建管理员
   */
  async createAdmin(data: Partial<Admin>): Promise<Admin> {
    return this.request<Admin>({
      method: 'POST',
      url: '/admins',
      data,
    });
  }

  /**
   * 更新管理员信息
   */
  async updateAdmin(id: number, data: Partial<Admin>): Promise<Admin> {
    return this.request<Admin>({
      method: 'PUT',
      url: `/admins/${id}`,
      data,
    });
  }

  /**
   * 删除管理员
   */
  async deleteAdmin(id: number): Promise<void> {
    return this.request<void>({
      method: 'DELETE',
      url: `/admins/${id}`,
    });
  }

  // ==================== 用户相关 API ====================

  /**
   * 获取用户列表
   */
  async getUsers(params?: {
    page?: number;
    per_page?: number;
    search?: string;
    is_admin?: boolean;
    is_block?: boolean;
    is_premium?: boolean;
    sort_by?: string;
    sort_order?: 'asc' | 'desc';
  }): Promise<PaginatedResponse<User>> {
    return this.request<PaginatedResponse<User>>({
      method: 'GET',
      url: '/users',
      params,
    });
  }

  /**
   * 获取单个用户信息
   */
  async getUser(id: number): Promise<User> {
    return this.request<User>({
      method: 'GET',
      url: `/users/${id}`,
    });
  }

  /**
   * 更新用户信息
   */
  async updateUser(id: number, data: Partial<User>): Promise<User> {
    return this.request<User>({
      method: 'PUT',
      url: `/users/${id}`,
      data,
    });
  }

  /**
   * 删除用户
   */
  async deleteUser(id: number): Promise<void> {
    return this.request<void>({
      method: 'DELETE',
      url: `/users/${id}`,
    });
  }

  /**
   * 导出用户数据
   */
  async exportUsers(format: 'csv' | 'xlsx' | 'json' = 'csv'): Promise<Blob> {
    const response = await this.client.request({
      method: 'GET',
      url: `/users/export?format=${format}`,
      responseType: 'blob',
    });
    return response.data;
  }
}

// 创建并导出 API 客户端实例
export const apiClient = new ApiClient();

// 导出常用方法的简化版本（绑定this上下文）
export const login = apiClient.login.bind(apiClient);
export const logout = apiClient.logout.bind(apiClient);
export const getCurrentUser = apiClient.getCurrentUser.bind(apiClient);
export const getDashboardStats = apiClient.getDashboardStats.bind(apiClient);
export const getAdmins = apiClient.getAdmins.bind(apiClient);
export const getAdmin = apiClient.getAdmin.bind(apiClient);
export const createAdmin = apiClient.createAdmin.bind(apiClient);
export const updateAdmin = apiClient.updateAdmin.bind(apiClient);
export const deleteAdmin = apiClient.deleteAdmin.bind(apiClient);
export const getUsers = apiClient.getUsers.bind(apiClient);
export const getUser = apiClient.getUser.bind(apiClient);
export const updateUser = apiClient.updateUser.bind(apiClient);
export const deleteUser = apiClient.deleteUser.bind(apiClient);
export const exportUsers = apiClient.exportUsers.bind(apiClient);