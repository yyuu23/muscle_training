/**
 * Settings page (plan §8.1 设置页): appearance (dual theme), profile entry,
 * memory candidate confirmation, password change, sync status, export,
 * logout.
 */

import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  ArrowRightIcon, CheckIcon, XMarkIcon, SunIcon, MoonIcon, ComputerDesktopIcon,
} from '@heroicons/react/24/outline';
import { apiGet, apiPost } from '../../api/client';
import { useAuth, useLogout } from '../auth/useAuth';
import { useSyncStatus } from '../../hooks/useSync';
import { useTheme, ThemeMode } from '../../hooks/useTheme';
import { outboxService } from '../../offline/outbox';
import { ConfirmAction } from '../../components/ConfirmAction';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { Sheet } from '../../components/ui/Sheet';

const SOURCE_KIND_LABELS: Record<string, string> = {
  user_statement: '你的陈述',
  reported_professional_advice: '转述的专业建议',
  reported_third_party: '他人转述',
  model_inference: '模型推断',
};

const THEME_OPTIONS: { value: ThemeMode; label: string; Icon: typeof SunIcon }[] = [
  { value: 'system', label: '跟随系统', Icon: ComputerDesktopIcon },
  { value: 'light', label: '浅色', Icon: SunIcon },
  { value: 'dark', label: '暗色', Icon: MoonIcon },
];

export function SettingsPage() {
  const { user, capabilities } = useAuth();
  const { status, pendingCount, needsAttentionCount, lastSyncedAt, isOnline, triggerSync } = useSyncStatus(user?.id ?? null);
  const { mode: themeMode, setTheme } = useTheme();
  const logout = useLogout();
  const queryClient = useQueryClient();

  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [passwordMessage, setPasswordMessage] = useState<string | null>(null);
  const [attentionOpen, setAttentionOpen] = useState(false);
  const [attentionItems, setAttentionItems] = useState<{ id: string; last_error: string | null }[]>([]);

  const candidatesQuery = useQuery({
    queryKey: ['memory-candidates'],
    queryFn: () => apiGet('/api/v1/profiles/memory-candidates'),
  });

  const [exportJobId, setExportJobId] = useState<string | null>(null);

  const exportQuery = useQuery({
    queryKey: ['exports', exportJobId],
    queryFn: () => apiGet('/api/v1/exports/{job_id}', { job_id: exportJobId! }),
    enabled: !!exportJobId,
    refetchInterval: (query) =>
      query.state.data && ['succeeded', 'failed'].includes(query.state.data.status) ? false : 2000,
  });

  const resolveCandidate = useMutation({
    mutationFn: ({ id, decision }: { id: string; decision: 'accept' | 'reject' }) =>
      apiPost('/api/v1/profiles/memory-candidates/{candidate_id}/resolve', { decision }, { candidate_id: id }),
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
    const result = await apiPost('/api/v1/exports');
    setExportJobId(result.job_id);
  };

  const openAttention = async () => {
    if (!user) return;
    const items = await outboxService.getNeedsAttention(user.id);
    setAttentionItems(items.map((i) => ({ id: i.event_id, last_error: i.last_error ?? null })));
    setAttentionOpen(true);
  };

  return (
    <div className="page-container py-6 space-y-5">
      <h1 className="text-2xl font-bold text-text">设置</h1>

      <div className="space-y-5 lg:grid lg:grid-cols-2 lg:gap-5 lg:items-start lg:space-y-0">
      <div className="space-y-5">

      {/* Account */}
      <div className="card p-5 animate-slide-up">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div
              className="w-12 h-12 rounded-2xl flex items-center justify-center text-lg font-bold text-primary-contrast"
              style={{ background: 'linear-gradient(135deg, var(--header-from), var(--header-to))' }}
            >
              {(user?.display_name ?? '?').slice(0, 1)}
            </div>
            <div>
              <p className="font-semibold text-text">{user?.display_name}</p>
              <p className="text-xs text-text-muted">
                {user?.username} · {user?.role === 'admin' ? '管理员' : '成员'}
              </p>
            </div>
          </div>
          <Link to="/onboarding" className="text-sm text-primary font-medium inline-flex items-center gap-1 hover:gap-1.5 transition-all">
            编辑档案 <ArrowRightIcon className="w-3.5 h-3.5" />
          </Link>
        </div>
        {capabilities && (
          <div className="mt-3 flex flex-wrap gap-2">
            <Badge tone={capabilities.chat_model_configured ? 'success' : 'neutral'}>
              {capabilities.chat_model_configured ? '模型已配置' : '模型未配置（记录不受影响）'}
            </Badge>
            <Badge tone={capabilities.content_ready ? 'success' : 'neutral'}>
              {capabilities.content_ready ? '内容就绪' : '内容未就绪'}
            </Badge>
          </div>
        )}
      </div>

      {/* Appearance */}
      <div className="card p-5 animate-slide-up" style={{ animationDelay: '50ms' }}>
        <h2 className="font-semibold mb-3">外观</h2>
        <div className="grid grid-cols-3 gap-2" role="radiogroup" aria-label="主题模式">
          {THEME_OPTIONS.map(({ value, label, Icon }) => (
            <button
              key={value}
              role="radio"
              aria-checked={themeMode === value}
              onClick={() => setTheme(value)}
              className={`flex flex-col items-center gap-1.5 py-3.5 rounded-2xl border transition-all duration-200 ${
                themeMode === value
                  ? 'border-primary bg-primary-soft text-primary shadow-soft scale-[1.02]'
                  : 'border-border-default text-text-secondary hover:border-border-strong'
              }`}
            >
              <Icon className="w-5 h-5" />
              <span className="text-xs font-medium">{label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Memory candidates */}
      <div className="card p-5 animate-slide-up" style={{ animationDelay: '100ms' }}>
        <h2 className="font-semibold mb-1">待确认记忆</h2>
        <p className="text-xs text-text-muted mb-3">
          模型从对话中提取的候选事实；确认后才会写入你的长期档案。
        </p>
        {candidatesQuery.isLoading ? (
          <p className="text-sm text-text-muted">加载中…</p>
        ) : candidatesQuery.data && candidatesQuery.data.length > 0 ? (
          <ul className="space-y-3">
            {candidatesQuery.data.map((c, i) => (
              <li
                key={c.id}
                className="border border-border-default rounded-xl p-3 animate-slide-up"
                style={{ animationDelay: `${i * 60}ms` }}
              >
                <p className="text-sm text-text">{c.proposed_fact}</p>
                <p className="text-xs text-text-muted mt-1">
                  来源：{SOURCE_KIND_LABELS[c.source_kind] ?? c.source_kind}
                </p>
                <div className="flex gap-2 mt-2.5">
                  <Button
                    size="sm"
                    onClick={() => resolveCandidate.mutate({ id: c.id, decision: 'accept' })}
                  >
                    <CheckIcon className="w-3.5 h-3.5" /> 确认
                  </Button>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => resolveCandidate.mutate({ id: c.id, decision: 'reject' })}
                  >
                    <XMarkIcon className="w-3.5 h-3.5" /> 忽略
                  </Button>
                </div>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-text-muted">没有待确认的记忆</p>
        )}
      </div>

      </div>
      <div className="space-y-5">

      {/* Sync */}
      <div className="card p-5 animate-slide-up" style={{ animationDelay: '150ms' }}>
        <h2 className="font-semibold mb-3">同步</h2>
        <div className="text-sm space-y-1.5">
          <p className="text-text">
            状态：
            <span className={isOnline ? 'text-success' : 'text-text-muted'}>
              {isOnline ? (status === 'syncing' ? '同步中…' : '在线') : '离线（记录保存在本机）'}
            </span>
          </p>
          <p className="text-text-secondary">
            待同步事件：{pendingCount} 条
            {needsAttentionCount > 0 && ` · ${needsAttentionCount} 条需处理`}
          </p>
          {lastSyncedAt && (
            <p className="text-xs text-text-muted">上次同步：{new Date(lastSyncedAt).toLocaleString('zh-CN')}</p>
          )}
        </div>
        <div className="flex gap-2 mt-3.5">
          <Button size="sm" onClick={triggerSync}>立即同步</Button>
          {needsAttentionCount > 0 && (
            <Button variant="secondary" size="sm" onClick={openAttention}>
              查看需处理事件
            </Button>
          )}
        </div>
      </div>

      {/* Password */}
      <div className="card p-5 animate-slide-up" style={{ animationDelay: '200ms' }}>
        <h2 className="font-semibold mb-3">修改密码</h2>
        <div className="space-y-2.5">
          <input
            type="password"
            placeholder="当前密码"
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
            className="input"
          />
          <input
            type="password"
            placeholder="新密码（至少12个字符）"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            className="input"
          />
          {passwordMessage && <p className="text-xs text-text-secondary">{passwordMessage}</p>}
          <Button size="sm" disabled={!currentPassword || !newPassword} onClick={changePassword}>
            修改密码
          </Button>
        </div>
      </div>

      {/* Export */}
      <div className="card p-5 animate-slide-up" style={{ animationDelay: '250ms' }}>
        <h2 className="font-semibold mb-1">导出我的数据</h2>
        <p className="text-xs text-text-muted mb-3">生成包含训练、测量、饮食与档案的 JSON 导出（24 小时内有效）</p>
        <Button size="sm" onClick={startExport} disabled={!!exportJobId}>
          {exportJobId ? (exportQuery.data?.status === 'succeeded' ? '导出完成' : '导出中…') : '开始导出'}
        </Button>
        {exportQuery.data?.status === 'succeeded' && exportQuery.data.download_url && (
          <a
            href={exportQuery.data.download_url}
            className="ml-3 text-sm text-primary font-medium underline underline-offset-4"
            download
          >
            下载
          </a>
        )}
      </div>

      </div>

      {/* Logout */}
      <div className="lg:col-span-2">
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
          <button onClick={trigger} className="btn btn-danger w-full py-3">
            退出登录
          </button>
        )}
      </ConfirmAction>
      </div>
      </div>

      {/* Needs-attention events */}
      <Sheet open={attentionOpen} onClose={() => setAttentionOpen(false)} title="需处理的同步事件">
        <p className="text-sm text-text-secondary mb-3">
          这些事件被服务器拒绝（通常是数据校验失败），已保留在本机。
        </p>
        <ul className="space-y-2 max-h-72 overflow-y-auto scrollbar-thin">
          {attentionItems.map((item) => (
            <li key={item.id} className="rounded-xl bg-surface-2 px-3 py-2.5 text-sm">
              <p className="text-text-muted text-xs font-mono break-all">{item.id}</p>
              <p className="text-danger mt-1">{item.last_error ?? '被拒绝'}</p>
            </li>
          ))}
          {attentionItems.length === 0 && <li className="text-sm text-text-muted">无</li>}
        </ul>
        <Button variant="secondary" className="w-full mt-4" onClick={() => setAttentionOpen(false)}>
          知道了
        </Button>
      </Sheet>
    </div>
  );
}
