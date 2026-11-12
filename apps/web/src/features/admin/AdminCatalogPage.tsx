/**
 * Admin content management (plan §8.1 管理内容页): import, validate,
 * review & publish exercises/templates.
 */

import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { CheckIcon, XMarkIcon, DocumentArrowUpIcon, ShieldCheckIcon } from '@heroicons/react/24/outline';
import { apiFetch } from '../../api/client';
import { useAuth } from '../auth/useAuth';

interface ContentItem {
  id: string;
  slug: string;
  content_version: number;
  name: string;
  review_status: 'draft' | 'approved' | 'rejected';
  fixture: boolean;
  reviewed_at: string | null;
}

const STATUS_STYLES: Record<string, string> = {
  draft: 'bg-amber-50 text-amber-700', approved: 'bg-green-50 text-green-700', rejected: 'bg-red-50 text-red-700',
};

export function AdminCatalogPage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [message, setMessage] = useState<string | null>(null);

  const isAdmin = user?.role === 'admin';

  const statsQuery = useQuery({
    queryKey: ['admin', 'stats'],
    queryFn: () =>
      apiFetch<{
        exercises_total: number; exercises_approved: number;
        templates_total: number; templates_approved: number; content_ready: boolean;
      }>('/admin/catalog/stats'),
    enabled: isAdmin,
  });

  const exercisesQuery = useQuery({
    queryKey: ['admin', 'exercises'],
    queryFn: () => apiFetch<ContentItem[]>('/admin/catalog/exercises'),
    enabled: isAdmin,
  });

  const templatesQuery = useQuery({
    queryKey: ['admin', 'templates'],
    queryFn: () => apiFetch<ContentItem[]>('/admin/catalog/templates'),
    enabled: isAdmin,
  });

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ['admin'] });
  };

  const importContent = useMutation({
    mutationFn: (kind: 'exercises' | 'templates') =>
      apiFetch<{ imported: number; skipped: number }>('/admin/catalog/import', {
        method: 'POST',
        body: { content_root: 'content', kind },
      }),
    onSuccess: (r) => {
      setMessage(`导入完成：成功 ${r.imported}，跳过 ${r.skipped}`);
      invalidate();
    },
    onError: (e) => setMessage(e instanceof Error ? e.message : '导入失败'),
  });

  const review = useMutation({
    mutationFn: ({ kind, id, decision }: { kind: string; id: string; decision: 'approve' | 'reject' }) =>
      apiFetch(`/admin/catalog/${kind}/${id}/review`, { method: 'POST', body: { decision } }),
    onSuccess: invalidate,
  });

  if (!isAdmin) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-10 text-center text-sm text-gray-500">
        仅管理员可访问内容管理。
      </div>
    );
  }

  const renderList = (title: string, kind: 'exercises' | 'templates', items: ContentItem[] | undefined) => (
    <div className="card p-5">
      <h2 className="font-semibold mb-3">{title}</h2>
      {items ? (
        <ul className="divide-y divide-gray-50">
          {items.map((item) => (
            <li key={item.id} className="py-3 flex items-center justify-between gap-3">
              <div className="min-w-0">
                <p className="text-sm text-gray-800 truncate">
                  {item.name} <span className="text-xs text-gray-400">v{item.content_version}</span>
                  {item.fixture && <span className="ml-1 text-[10px] bg-gray-100 text-gray-500 px-1 rounded">测试</span>}
                </p>
                <p className="text-xs text-gray-400">{item.slug}</p>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <span className={`text-xs px-2 py-0.5 rounded-full ${STATUS_STYLES[item.review_status]}`}>
                  {item.review_status === 'draft' ? '待审核' : item.review_status === 'approved' ? '已发布' : '已拒绝'}
                </span>
                {item.review_status === 'draft' && (
                  <>
                    <button
                      onClick={() => review.mutate({ kind, id: item.id, decision: 'approve' })}
                      className="p-1.5 rounded-lg bg-green-50 text-green-700 hover:bg-green-100"
                      title="审核通过"
                    >
                      <CheckIcon className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => review.mutate({ kind, id: item.id, decision: 'reject' })}
                      className="p-1.5 rounded-lg bg-red-50 text-red-600 hover:bg-red-100"
                      title="拒绝"
                    >
                      <XMarkIcon className="w-4 h-4" />
                    </button>
                  </>
                )}
              </div>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-gray-400">加载中…</p>
      )}
    </div>
  );

  return (
    <div className="max-w-2xl mx-auto px-4 py-6 space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">内容管理</h1>

      {/* Stats */}
      {statsQuery.data && (
        <div className="card p-5">
          <div className="flex items-center gap-2 mb-3">
            <ShieldCheckIcon className="w-5 h-5 text-primary-600" />
            <span className={`text-sm font-medium ${statsQuery.data.content_ready ? 'text-green-700' : 'text-amber-700'}`}>
              {statsQuery.data.content_ready ? '内容已就绪（计划功能可用）' : '内容未就绪：需要至少一份已审核模板与动作'}
            </span>
          </div>
          <div className="grid grid-cols-2 gap-3 text-sm text-gray-600">
            <p>动作：{statsQuery.data.exercises_approved}/{statsQuery.data.exercises_total} 已发布</p>
            <p>模板：{statsQuery.data.templates_approved}/{statsQuery.data.templates_total} 已发布</p>
          </div>
        </div>
      )}

      {/* Import actions */}
      <div className="card p-5">
        <h2 className="font-semibold mb-1">从内容目录导入</h2>
        <p className="text-xs text-gray-400 mb-3">
          导入 YAML 文件为草稿（fixture=true 的内容生产环境自动排除）；发布需逐项审核。
        </p>
        <div className="flex gap-2">
          <button
            onClick={() => importContent.mutate('exercises')}
            disabled={importContent.isPending}
            className="btn-primary px-4 py-2 text-sm inline-flex items-center gap-2"
          >
            <DocumentArrowUpIcon className="w-4 h-4" /> 导入动作
          </button>
          <button
            onClick={() => importContent.mutate('templates')}
            disabled={importContent.isPending}
            className="btn-primary px-4 py-2 text-sm inline-flex items-center gap-2"
          >
            <DocumentArrowUpIcon className="w-4 h-4" /> 导入模板
          </button>
        </div>
        {message && <p className="text-xs text-gray-600 mt-2">{message}</p>}
      </div>

      {renderList('动作目录', 'exercises', exercisesQuery.data)}
      {renderList('训练模板', 'templates', templatesQuery.data)}
    </div>
  );
}
