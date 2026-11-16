/**
 * Admin content management (plan §8.1 管理内容页): import, validate,
 * review & publish exercises/templates.
 */

import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { CheckIcon, XMarkIcon, DocumentArrowUpIcon, ShieldCheckIcon } from '@heroicons/react/24/solid';
import { apiFetch } from '../../api/client';
import { useAuth } from '../auth/useAuth';
import { Badge } from '../../components/ui/Badge';
import type { BadgeTone } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';

interface ContentItem {
  id: string;
  slug: string;
  content_version: number;
  name: string;
  review_status: 'draft' | 'approved' | 'rejected';
  fixture: boolean;
  reviewed_at: string | null;
}

const STATUS_TONES: Record<string, BadgeTone> = {
  draft: 'warning', approved: 'success', rejected: 'danger',
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
      <div className="page-container py-10 text-center text-sm text-text-secondary">
        仅管理员可访问内容管理。
      </div>
    );
  }

  const renderList = (title: string, kind: 'exercises' | 'templates', items: ContentItem[] | undefined) => (
    <div className="card p-5 animate-slide-up">
      <h2 className="font-semibold text-text mb-3">{title}</h2>
      {items ? (
        <ul className="divide-y divide-border-default/60">
          {items.map((item, i) => (
            <li
              key={item.id}
              className="py-3 flex items-center justify-between gap-3 animate-fade-in"
              style={{ animationDelay: `${Math.min(i, 10) * 30}ms` }}
            >
              <div className="min-w-0">
                <p className="text-sm text-text truncate flex items-center gap-1.5">
                  {item.name} <span className="text-xs text-text-muted">v{item.content_version}</span>
                  {item.fixture && <Badge tone="neutral" className="!text-[10px] !px-1.5">测试</Badge>}
                </p>
                <p className="text-xs text-text-muted mt-0.5">{item.slug}</p>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <Badge tone={STATUS_TONES[item.review_status]}>
                  {item.review_status === 'draft' ? '待审核' : item.review_status === 'approved' ? '已发布' : '已拒绝'}
                </Badge>
                {item.review_status === 'draft' && (
                  <>
                    <button
                      onClick={() => review.mutate({ kind, id: item.id, decision: 'approve' })}
                      className="p-1.5 rounded-xl bg-success-soft text-success hover:brightness-95 transition-all"
                      title="审核通过"
                    >
                      <CheckIcon className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => review.mutate({ kind, id: item.id, decision: 'reject' })}
                      className="p-1.5 rounded-xl bg-danger-soft text-danger hover:brightness-95 transition-all"
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
        <p className="text-sm text-text-muted">加载中…</p>
      )}
    </div>
  );

  return (
    <div className="page-container py-6 space-y-5">
      <h1 className="text-2xl font-bold text-text">内容管理</h1>

      {/* Stats */}
      {statsQuery.data && (
        <div className="card p-5 animate-slide-up">
          <div className="flex items-center gap-2 mb-3">
            <ShieldCheckIcon className="w-5 h-5 text-primary" />
            <span className={`text-sm font-medium ${statsQuery.data.content_ready ? 'text-success' : 'text-warning'}`}>
              {statsQuery.data.content_ready ? '内容已就绪（计划功能可用）' : '内容未就绪：需要至少一份已审核模板与动作'}
            </span>
          </div>
          <div className="grid grid-cols-2 gap-3 text-sm text-text-secondary tabular-nums">
            <p>动作：{statsQuery.data.exercises_approved}/{statsQuery.data.exercises_total} 已发布</p>
            <p>模板：{statsQuery.data.templates_approved}/{statsQuery.data.templates_total} 已发布</p>
          </div>
        </div>
      )}

      {/* Import actions */}
      <div className="card p-5 animate-slide-up" style={{ animationDelay: '60ms' }}>
        <h2 className="font-semibold mb-1">从内容目录导入</h2>
        <p className="text-xs text-text-muted mb-3 leading-relaxed">
          导入 YAML 文件为草稿（fixture=true 的内容生产环境自动排除）；发布需逐项审核。
        </p>
        <div className="flex gap-2">
          <Button
            size="sm"
            onClick={() => importContent.mutate('exercises')}
            loading={importContent.isPending}
          >
            <DocumentArrowUpIcon className="w-4 h-4" /> 导入动作
          </Button>
          <Button
            size="sm"
            onClick={() => importContent.mutate('templates')}
            loading={importContent.isPending}
          >
            <DocumentArrowUpIcon className="w-4 h-4" /> 导入模板
          </Button>
        </div>
        {message && <p className="text-xs text-text-secondary mt-2">{message}</p>}
      </div>

      {renderList('动作目录', 'exercises', exercisesQuery.data)}
      {renderList('训练模板', 'templates', templatesQuery.data)}
    </div>
  );
}
