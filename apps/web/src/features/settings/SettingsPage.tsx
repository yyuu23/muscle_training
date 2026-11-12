/**
 * Settings page (plan §8.1 设置页): profile entry, memory candidate
 * confirmation, password change, sync status, export, logout.
 */

import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ArrowRightIcon, CheckIcon, XMarkIcon } from '@heroicons/react/24/outline';
import { apiFetch } from '../../api/client';
import { useAuth, useLogout } from '../auth/useAuth';
import { useSyncStatus } from '../../hooks/useSync';
import { outboxService } from '../../offline/outbox';
import { ConfirmAction } from '../../components/ConfirmAction';

interface MemoryCandidate {
  id: string;
  proposed_fact: string;
  source_kind: string;
  status: string;
  metadata: { kind?: string } | null;
}

const SOURCE_KIND_LABELS: Record<string, string> = {
  user_statement: '你的陈述',
  reported_professional_advice: '转述的专业建议',
  reported_third_party: '他人转述',
  model_inference: '模型推断',
};

export function SettingsPage() {
  const { user, capabilities } = useAuth();
  const { status, pendingCount, needsAttentionCount, lastSyncedAt, isOnline, triggerSync } = useSyncStatus(user?.id ?? null);
  const logout = useLogout();
  const queryClient = useQueryClient();

  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [passwordMessage, setPasswordMessage] = useState<string | null>(null);

  const candidatesQuery = useQuery({
    queryKey: ['memory-candidates'],
    queryFn: () => apiFetch<MemoryCandidate[]>('/profiles/memory-candidates'),
  });

  const [exportJobId, setExportJobId] = useState<string | null>(null);

  const exportQuery = useQuery({
    queryKey: ['exports', exportJobId],
    queryFn: () => apiFetch<{ status: string; download_url: string | null }>(`/exports/${exportJobId}`),
    enabled: !!exportJobId,
    refetchInterval: (query) =>
      query.state.data && ['succeeded', 'failed'].includes(query.state.data.status) ? false : 2000,
  });

  const resolveCandidate = useMutation({
    mutationFn: ({ id, decision }: { id: string; decision: 'accept' | 'reject' }) =>
      apiFetch(`/profiles/memory-candidates/${id}/resolve`, { method: 'POST', body: { decision } }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['memory-candidates'] }),
  });

  const changePassword = async () => {
    setPasswordMessage(null);
    if (newPassword.length < 12) {
      setPasswordMessage('新密码至少 12 个字符');
      return;
    }
    try {
      const { changePassword: doChange } = await import('../../api/auth');
      await doChange(currentPassword, newPassword);
      setPasswordMessage('密码已修改，其他设备会话已撤销');
      setCurrentPassword('');
      setNewPassword('');
    } catch (err) {
      setPasswordMessage(err instanceof Error ? err.message : '修改失败');
    }
  };

  const startExport = async () => {
    const result = await apiFetch<{ job_id: string }>('/exports', { method: 'POST' });
    setExportJobId(result.job_id);
  };

  return (
    <div className="max-w-2xl mx-auto px-4 py-6 space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">设置</h1>

      {/* Account */}
      <div className="card p-5">
        <div className="flex items-center justify-between">
          <div>
            <p className="font-semibold text-gray-900">{user?.display_name}</p>
            <p className="text-xs text-gray-400">
              {user?.username} · {user?.role === 'admin' ? '管理员' : '成员'}
            </p>
          </div>
          <Link to="/onboarding" className="text-sm text-primary-600 inline-flex items-center gap-1">
            编辑档案 <ArrowRightIcon className="w-3 h-3" />
          </Link>
        </div>
        {capabilities && (
          <div className="mt-3 flex flex-wrap gap-2 text-xs">
            <span className={`px-2 py-1 rounded-full ${capabilities.chat_model_configured ? 'bg-green-50 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
              {capabilities.chat_model_configured ? '模型已配置' : '模型未配置（记录不受影响）'}
            </span>
            <span className={`px-2 py-1 rounded-full ${capabilities.content_ready ? 'bg-green-50 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
              {capabilities.content_ready ? '内容就绪' : '内容未就绪'}
            </span>
          </div>
        )}
      </div>

      {/* Memory candidates */}
      <div className="card p-5">
        <h2 className="font-semibold mb-1">待确认记忆</h2>
        <p className="text-xs text-gray-400 mb-3">
          模型从对话中提取的候选事实；确认后才会写入你的长期档案。
        </p>
        {candidatesQuery.isLoading ? (
          <p className="text-sm text-gray-400">加载中…</p>
        ) : candidatesQuery.data && candidatesQuery.data.length > 0 ? (
          <ul className="space-y-3">
            {candidatesQuery.data.map((c) => (
              <li key={c.id} className="border border-gray-100 rounded-xl p-3">
                <p className="text-sm text-gray-800">{c.proposed_fact}</p>
                <p className="text-xs text-gray-400 mt-1">
                  来源：{SOURCE_KIND_LABELS[c.source_kind] ?? c.source_kind}
                </p>
                <div className="flex gap-2 mt-2">
                  <button
                    onClick={() => resolveCandidate.mutate({ id: c.id, decision: 'accept' })}
                    className="btn-primary px-3 py-1.5 text-xs inline-flex items-center gap-1"
                  >
                    <CheckIcon className="w-3 h-3" /> 确认
                  </button>
                  <button
                    onClick={() => resolveCandidate.mutate({ id: c.id, decision: 'reject' })}
                    className="px-3 py-1.5 text-xs rounded-lg border border-gray-200 text-gray-600 inline-flex items-center gap-1"
                  >
                    <XMarkIcon className="w-3 h-3" /> 忽略
                  </button>
                </div>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-gray-400">没有待确认的记忆</p>
        )}
      </div>

      {/* Sync */}
      <div className="card p-5">
        <h2 className="font-semibold mb-3">同步</h2>
        <div className="text-sm space-y-1">
          <p>
            状态：
            <span className={isOnline ? 'text-green-600' : 'text-gray-400'}>
              {isOnline ? (status === 'syncing' ? '同步中…' : '在线') : '离线（记录保存在本机）'}
            </span>
          </p>
          <p className="text-gray-500">待同步事件：{pendingCount} 条{needsAttentionCount > 0 && ` · ${needsAttentionCount} 条需处理`}</p>
          {lastSyncedAt && <p className="text-xs text-gray-400">上次同步：{new Date(lastSyncedAt).toLocaleString('zh-CN')}</p>}
        </div>
        <div className="flex gap-2 mt-3">
          <button onClick={triggerSync} className="btn-primary px-4 py-2 text-sm">立即同步</button>
          {needsAttentionCount > 0 && (
            <button
              onClick={async () => {
                if (!user) return;
                const items = await outboxService.getNeedsAttention(user.id);
                alert(items.map((i) => i.last_error ?? '被拒绝').join('\n'));
              }}
              className="px-4 py-2 text-sm rounded-lg border border-amber-200 text-amber-700"
            >
              查看需处理事件
            </button>
          )}
        </div>
      </div>

      {/* Password */}
      <div className="card p-5">
        <h2 className="font-semibold mb-3">修改密码</h2>
        <div className="space-y-2">
          <input
            type="password"
            placeholder="当前密码"
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
            className="input w-full"
          />
          <input
            type="password"
            placeholder="新密码（至少12个字符）"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            className="input w-full"
          />
          {passwordMessage && <p className="text-xs text-gray-600">{passwordMessage}</p>}
          <button onClick={changePassword} disabled={!currentPassword || !newPassword} className="btn-primary px-4 py-2 text-sm">
            修改密码
          </button>
        </div>
      </div>

      {/* Export */}
      <div className="card p-5">
        <h2 className="font-semibold mb-1">导出我的数据</h2>
        <p className="text-xs text-gray-400 mb-3">生成包含训练、测量、饮食与档案的 JSON 导出（24 小时内有效）</p>
        <button onClick={startExport} className="btn-primary px-4 py-2 text-sm" disabled={!!exportJobId}>
          {exportJobId ? (exportQuery.data?.status === 'succeeded' ? '导出完成' : '导出中…') : '开始导出'}
        </button>
        {exportQuery.data?.status === 'succeeded' && exportQuery.data.download_url && (
          <a
            href={exportQuery.data.download_url}
            className="ml-3 text-sm text-primary-600 underline"
            download
          >
            下载
          </a>
        )}
      </div>

      {/* Logout */}
      <ConfirmAction
        title="退出登录？"
        description={
          pendingCount > 0
            ? `本机还有 ${pendingCount} 条未同步记录，退出后这些记录只保存在本机，重新登录后可继续同步。`
            : '确认退出当前账号。'
        }
        confirmLabel="退出"
        onConfirm={async () => {
          await logout.mutateAsync();
        }}
      >
        {(trigger) => (
          <button onClick={trigger} className="w-full py-3 text-sm text-red-600 border border-red-100 rounded-xl hover:bg-red-50">
            退出登录
          </button>
        )}
      </ConfirmAction>
    </div>
  );
}
