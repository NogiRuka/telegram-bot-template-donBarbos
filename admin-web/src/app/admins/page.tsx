'use client';

import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { 
  Table, 
  TableBody, 
  TableCell, 
  TableHead, 
  TableHeader, 
  TableRow 
} from '@/components/ui/table';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { 
  Search, 
  Plus, 
  MoreHorizontal, 
  Edit, 
  Trash2,
  RefreshCw,
  Shield,
  UserCheck,
  Crown
} from 'lucide-react';
import { getAdmins, createAdmin, updateAdmin, deleteAdmin } from '@/lib/api';
import { Admin, PaginatedResponse } from '@/types';

/**
 * 管理员角色徽章组件
 */
function AdminRoleBadge({ roles }: { roles: string[] }) {
  const primaryRole = roles[0] || 'user';
  const variant = primaryRole === 'admin' ? 'default' : 'secondary';
  
  return (
    <Badge variant={variant}>
      {primaryRole === 'admin' ? '管理员' : '用户'}
    </Badge>
  );
}

/**
 * 管理员状态徽章组件
 */
function AdminStatusBadge({ isActive }: { isActive: boolean }) {
  return (
    <Badge variant={isActive ? "default" : "destructive"}>
      {isActive ? '活跃' : '禁用'}
    </Badge>
  );
}

/**
 * 创建/编辑管理员对话框组件
 */
interface AdminDialogProps {
  admin?: Admin;
  isOpen: boolean;
  onClose: () => void;
  onSave: (admin: Partial<Admin>) => void;
}

function AdminDialog({ admin, isOpen, onClose, onSave }: AdminDialogProps) {
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    active: true,
  });

  useEffect(() => {
    if (admin) {
      setFormData({
        email: admin.email,
        password: '',
        active: admin.active,
      });
    } else {
      setFormData({
        email: '',
        password: '',
        active: true,
      });
    }
  }, [admin, isOpen]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave(formData);
    onClose();
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>
            {admin ? '编辑管理员' : '创建管理员'}
          </DialogTitle>
          <DialogDescription>
            {admin ? '修改管理员信息' : '创建新的管理员账户'}
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit}>
          <div className="grid gap-4 py-4">
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="email" className="text-right">
                邮箱
              </Label>
              <Input
                id="email"
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                className="col-span-3"
                required
              />
            </div>
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="password" className="text-right">
                密码
              </Label>
              <Input
                id="password"
                type="password"
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                className="col-span-3"
                placeholder={admin ? "留空表示不修改密码" : "请输入密码"}
                required={!admin}
              />
            </div>
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="active" className="text-right">
                状态
              </Label>
              <div className="col-span-3">
                <input
                  id="active"
                  type="checkbox"
                  checked={formData.active}
                  onChange={(e) => setFormData({ ...formData, active: e.target.checked })}
                  className="mr-2"
                />
                <span className="text-sm">启用账户</span>
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose}>
              取消
            </Button>
            <Button type="submit">
              {admin ? '更新' : '创建'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

/**
 * 管理员管理页面组件
 */
export default function AdminsPage() {
  const [admins, setAdmins] = useState<Admin[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalAdmins, setTotalAdmins] = useState(0);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [editingAdmin, setEditingAdmin] = useState<Admin | undefined>();
  const pageSize = 10;

  /**
   * 获取管理员列表
   */
  const fetchAdmins = async (page: number = 1, search: string = '') => {
    try {
      setIsLoading(true);
      setError(null);
      
      const response: PaginatedResponse<Admin> = await getAdmins({
        page,
        per_page: pageSize,
        search: search || undefined,
      });
      
      setAdmins(response.items);
      setCurrentPage(response.page);
      setTotalPages(response.pages);
      setTotalAdmins(response.total);
    } catch (err: any) {
      setError(err.message || '获取管理员列表失败');
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * 处理搜索
   */
  const handleSearch = (value: string) => {
    setSearchTerm(value);
    setCurrentPage(1);
    fetchAdmins(1, value);
  };

  /**
   * 处理创建/更新管理员
   */
  const handleSaveAdmin = async (adminData: Partial<Admin>) => {
    try {
      if (editingAdmin) {
        await updateAdmin(editingAdmin.id, adminData);
      } else {
        await createAdmin(adminData);
      }
      // 重新获取管理员列表
      fetchAdmins(currentPage, searchTerm);
      setEditingAdmin(undefined);
    } catch (err: any) {
      setError(err.message || '保存管理员失败');
    }
  };

  /**
   * 处理删除管理员
   */
  const handleDeleteAdmin = async (adminId: string) => {
    if (!confirm('确定要删除这个管理员吗？此操作不可撤销。')) {
      return;
    }

    try {
      await deleteAdmin(adminId);
      // 重新获取管理员列表
      fetchAdmins(currentPage, searchTerm);
    } catch (err: any) {
      setError(err.message || '删除管理员失败');
    }
  };

  /**
   * 处理编辑管理员
   */
  const handleEditAdmin = (admin: Admin) => {
    setEditingAdmin(admin);
    setIsDialogOpen(true);
  };

  /**
   * 处理创建新管理员
   */
  const handleCreateAdmin = () => {
    setEditingAdmin(undefined);
    setIsDialogOpen(true);
  };

  /**
   * 处理分页
   */
  const handlePageChange = (page: number) => {
    setCurrentPage(page);
    fetchAdmins(page, searchTerm);
  };

  useEffect(() => {
    fetchAdmins();
  }, []);

  return (
    <div className="space-y-6">
      {/* 页面头部 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">管理员管理</h1>
          <p className="text-muted-foreground">
            管理系统管理员账户和权限
          </p>
        </div>
        <Button onClick={handleCreateAdmin}>
          <Plus className="h-4 w-4 mr-2" />
          添加管理员
        </Button>
      </div>

      {/* 统计卡片 */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">总管理员</CardTitle>
            <Shield className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{totalAdmins}</div>
            <p className="text-xs text-muted-foreground">
              系统管理员总数
            </p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">活跃管理员</CardTitle>
            <UserCheck className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {admins.filter(admin => admin.active).length}
            </div>
            <p className="text-xs text-muted-foreground">
              当前页面活跃管理员
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">超级管理员</CardTitle>
            <Crown className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {admins.filter(admin => admin.roles.includes('admin')).length}
            </div>
            <p className="text-xs text-muted-foreground">
              拥有完整权限
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">在线管理员</CardTitle>
            <UserCheck className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">3</div>
            <p className="text-xs text-muted-foreground">
              当前在线管理员
            </p>
          </CardContent>
        </Card>
      </div>

      {/* 搜索和管理员列表 */}
      <Card>
        <CardHeader>
          <CardTitle>管理员列表</CardTitle>
          <CardDescription>
            查看和管理所有系统管理员
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center space-x-2 mb-4">
            <div className="relative flex-1">
              <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="搜索管理员邮箱..."
                value={searchTerm}
                onChange={(e) => handleSearch(e.target.value)}
                className="pl-8"
              />
            </div>
            <Button 
              variant="outline" 
              size="icon"
              onClick={() => fetchAdmins(currentPage, searchTerm)}
              disabled={isLoading}
            >
              <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
            </Button>
          </div>

          {/* 错误提示 */}
          {error && (
            <Alert variant="destructive" className="mb-4">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {/* 管理员表格 */}
          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>管理员信息</TableHead>
                  <TableHead>邮箱</TableHead>
                  <TableHead>角色</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>创建时间</TableHead>
                  <TableHead>最后登录</TableHead>
                  <TableHead className="text-right">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {isLoading ? (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center py-8">
                      <RefreshCw className="h-6 w-6 animate-spin mx-auto mb-2" />
                      加载中...
                    </TableCell>
                  </TableRow>
                ) : admins.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center py-8">
                      {searchTerm ? '未找到匹配的管理员' : '暂无管理员数据'}
                    </TableCell>
                  </TableRow>
                ) : (
                  admins.map((admin) => (
                    <TableRow key={admin.id}>
                      <TableCell>
                        <div className="flex items-center space-x-3">
                          <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center">
                            <Shield className="h-4 w-4" />
                          </div>
                          <div>
                            <div className="font-medium">{admin.email}</div>
                            <div className="text-sm text-muted-foreground">
                              ID: {admin.id}
                            </div>
                          </div>
                        </div>
                      </TableCell>
                      <TableCell>{admin.email}</TableCell>
                      <TableCell>
                        <AdminRoleBadge roles={admin.roles} />
                      </TableCell>
                      <TableCell>
                        <AdminStatusBadge isActive={admin.active} />
                      </TableCell>
                      <TableCell>
                        {admin.created_at ? new Date(admin.created_at).toLocaleDateString() : '-'}
                      </TableCell>
                      <TableCell>
                        {admin.last_login_at ? new Date(admin.last_login_at).toLocaleDateString() : '从未登录'}
                      </TableCell>
                      <TableCell className="text-right">
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" className="h-8 w-8 p-0">
                              <span className="sr-only">打开菜单</span>
                              <MoreHorizontal className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuLabel>操作</DropdownMenuLabel>
                            <DropdownMenuItem onClick={() => handleEditAdmin(admin)}>
                              <Edit className="mr-2 h-4 w-4" />
                              编辑管理员
                            </DropdownMenuItem>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem 
                              className="text-destructive"
                              onClick={() => handleDeleteAdmin(admin.id)}
                            >
                              <Trash2 className="mr-2 h-4 w-4" />
                              删除管理员
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>

          {/* 分页 */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between space-x-2 py-4">
              <div className="text-sm text-muted-foreground">
                显示第 {(currentPage - 1) * pageSize + 1} - {Math.min(currentPage * pageSize, totalAdmins)} 条，
                共 {totalAdmins} 条记录
              </div>
              <div className="flex items-center space-x-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handlePageChange(currentPage - 1)}
                  disabled={currentPage <= 1}
                >
                  上一页
                </Button>
                <div className="flex items-center space-x-1">
                  {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                    const page = i + 1;
                    return (
                      <Button
                        key={page}
                        variant={currentPage === page ? "default" : "outline"}
                        size="sm"
                        onClick={() => handlePageChange(page)}
                      >
                        {page}
                      </Button>
                    );
                  })}
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handlePageChange(currentPage + 1)}
                  disabled={currentPage >= totalPages}
                >
                  下一页
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* 创建/编辑管理员对话框 */}
      <AdminDialog
        admin={editingAdmin}
        isOpen={isDialogOpen}
        onClose={() => setIsDialogOpen(false)}
        onSave={handleSaveAdmin}
      />
    </div>
  );
}