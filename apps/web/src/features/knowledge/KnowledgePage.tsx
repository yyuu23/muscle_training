/**
 * Knowledge page (plan §8.1 知识库页): upload flow, import progress,
 * sources with status, chunks, temporary-file expiry, withdrawal.
 */

import { useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { DocumentArrowUpIcon } from '@heroicons/react/24/solid';
import { APIError, apiGet, apiPost } from '../../api/client';
import { EmptyState, ErrorState } from '../../components/ErrorState';
import { Badge } from '../../components/ui/Badge';
import type { BadgeTone } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { Sheet } from '../../components/ui/Sheet';
import { SkeletonCards } from '../../components/ui/Skeleton';

const STATUS_LABELS: Record<string, string> = {
  processing: '处理中', awaiting_review: '待审核', indexing: '索引中',
  ready: '可用', failed: '失败', withdrawn: '已撤回',
};
const STATUS_TONES: Record<string, BadgeTone> = {
  processing: 'primary', awaiting_review: 'warning',
  indexing: 'primary', ready: 'success',
  failed: 'danger', withdrawn: 'neutral',
};

function formatMs(ms: number | null): string {
  if (ms === null) return '';
  const s = Math.floor(ms / 1000);
  return `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`;
}

export function KnowledgePage() {
  const queryClient = useQueryClient();
  const fileInput = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [detailId, setDetailId] = useState<string | null>(null);
  // pending import: asset verified, waiting for the user to name it
  const [pendingImport, setPendingImport] = useState<{ assetId: string; defaultTitle: string } | null>(null);
  const [importTitle, setImportTitle] = useState('');

  const sourcesQuery = useQuery({
    queryKey: ['knowledge', 'sources'],
    queryFn: () => apiGet('/api/v1/knowledge/sources'),
    refetchInterval: 8000,
  });

  const detailQuery = useQuery({
    queryKey: ['knowledge', detailId],
    queryFn: () => apiGet('/api/v1/knowledge/sources/{source_id}', { source_id: detailId! }),
    enabled: !!detailId,
  });

  const withdraw = useMutation({
    mutationFn: (id: string) =>
      apiPost('/api/v1/knowledge/sources/{source_id}/withdraw', undefined, { source_id: id }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['knowledge'] }),
  });

  const handleFile = async (file: File) => {
    setUploadError(null);
    setUploading(`正在上传 ${file.name}…`);
    try {
      const created = await apiPost('/api/v1/knowledge/assets/uploads', {
        filename: file.name,
        content_type: file.type || 'application/octet-stream',
        byte_size: file.size,
      });

      // Upload via the grant (filesystem dev backend points at our API;
      // OSS would be an absolute presigned URL — same code path).
      const uploadResp = await fetch(created.upload.url, {
        method: created.upload.method || 'PUT',
        headers: created.upload.headers,
        credentials: 'same-origin',
        body: await file.arrayBuffer(),
      });
      if (!uploadResp.ok) {
        throw new Error(`上传失败 (${uploadResp.status})`);
      }

      const digest = await crypto.subtle.digest('SHA-256', await file.arrayBuffer());
      const sha256 = Array.from(new Uint8Array(digest)).map((b) => b.toString(16).padStart(2, '0')).join('');

      const completed = await apiPost(
        '/api/v1/knowledge/assets/{asset_id}/complete',
        { sha256 },
        { asset_id: created.asset_id },
      );
      if (!completed.verified) {
        throw new Error(completed.detail ?? '上传校验失败');
      }

      // Ask for the title in a proper sheet instead of window.prompt
      setUploading(null);
      setImportTitle(file.name.replace(/\.[^.]+$/, ''));
      setPendingImport({ assetId: created.asset_id, defaultTitle: file.name.replace(/\.[^.]+$/, '') });
    } catch (err) {
      setUploadError(err instanceof APIError ? err.message : err instanceof Error ? err.message : '上传失败');
      setUploading(null);
    }
  };

  const confirmImport = async () => {
    if (!pendingImport) return;
    const title = importTitle.trim() || pendingImport.defaultTitle;
    try {
      await apiPost('/api/v1/knowledge/imports', {
        asset_id: pendingImport.assetId,
        title,
      });
      setUploading('已提交导入任务，处理中…');
      await queryClient.invalidateQueries({ queryKey: ['knowledge'] });
      setTimeout(() => setUploading(null), 3000);
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : '导入失败');
    } finally {
      setPendingImport(null);
    }
  };

  return (
    <div className="page-container py-6 space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-text">知识库</h1>
        <>
          <input
            ref={fileInput}
            type="file"
            accept=".txt,.md,.srt,.vtt,.mp3,.m4a,.wav,.mp4"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) void handleFile(file);
              e.target.value = '';
            }}
          />
          <Button size="sm" onClick={() => fileInput.current?.click()} disabled={!!uploading}>
            <DocumentArrowUpIcon className="w-4 h-4" />
            上传资料
          </Button>
        </>
      </div>

      <p className="text-xs text-text-muted leading-relaxed">
        支持 TXT/Markdown/字幕(SRT/VTT)/音频/MP4。原视频与音频最多保留 7 天；转写与字幕长期保存。
        审核通过后才会用于教练回答。
      </p>

      {uploading && <div className="card !py-3 text-sm text-text-secondary animate-fade-in">{uploading}</div>}
      {uploadError && <div className="card !py-3 text-sm text-danger !bg-danger-soft !border-danger/30 animate-scale-in">{uploadError}</div>}

      {/* Sources */}
      {sourcesQuery.isLoading ? (
        <SkeletonCards count={3} />
      ) : sourcesQuery.isError ? (
        <ErrorState message="无法加载知识库" onRetry={() => void sourcesQuery.refetch()} />
      ) : sourcesQuery.data?.items.length ? (
        <ul className="space-y-2.5">
          {sourcesQuery.data.items.map((source, i) => (
            <li
              key={source.id}
              className="card p-4 animate-slide-up"
              style={{ animationDelay: `${Math.min(i, 8) * 50}ms` }}
            >
              <button className="w-full text-left" onClick={() => setDetailId(detailId === source.id ? null : source.id)}>
                <div className="flex items-center justify-between gap-2">
                  <span className="font-medium text-sm text-text truncate">{source.title}</span>
                  <Badge tone={STATUS_TONES[source.status] ?? 'neutral'}>
                    {STATUS_LABELS[source.status]}
                  </Badge>
                </div>
                <p className="text-xs text-text-muted mt-1">
                  {source.source_type === 'video' ? '视频' : source.source_type === 'audio' ? '音频'
                    : source.source_type === 'subtitle' ? '字幕' : '文档'}
                  {' · '}
                  {source.visibility === 'shared' ? '共享' : '私有'}
                  {' · '}
                  {new Date(source.updated_at).toLocaleDateString('zh-CN')}
                </p>
              </button>

              {detailId === source.id && (
                <div className="mt-3 border-t border-border-default pt-3 space-y-3 animate-fade-in">
                  {detailQuery.data ? (
                    <>
                      <div className="text-xs text-text-secondary">
                        修订 {detailQuery.data.revisions.length} 个；片段 {detailQuery.data.chunks.length} 条
                      </div>
                      <div className="max-h-64 overflow-y-auto space-y-2 scrollbar-thin">
                        {detailQuery.data.chunks.slice(0, 30).map((chunk) => (
                          <div key={chunk.id} className="bg-surface-2 rounded-xl p-2.5 text-xs">
                            {chunk.start_ms !== null && (
                              <span className="text-primary font-mono mr-2">{formatMs(chunk.start_ms)}</span>
                            )}
                            <span className="text-text-secondary line-clamp-3">{chunk.original_text}</span>
                          </div>
                        ))}
                      </div>
                      {source.status === 'ready' && (
                        <button
                          onClick={() => withdraw.mutate(source.id)}
                          className="btn btn-danger btn-sm text-xs"
                        >
                          撤回（不再用于新回答）
                        </button>
                      )}
                    </>
                  ) : (
                    <p className="text-xs text-text-muted">加载详情…</p>
                  )}
                </div>
              )}
            </li>
          ))}
        </ul>
      ) : (
        <div className="card p-6">
          <EmptyState
            title="还没有知识资料"
            description="上传健身视频字幕、转写音频或文档，审核后教练回答可以引用它们"
          />
        </div>
      )}

      {/* Import naming sheet */}
      <Sheet open={!!pendingImport} onClose={() => setPendingImport(null)} title="资料标题">
        <p className="text-sm text-text-secondary mb-3">为这份资料取一个便于检索的标题。</p>
        <input
          className="input"
          value={importTitle}
          onChange={(e) => setImportTitle(e.target.value)}
          placeholder={pendingImport?.defaultTitle}
          autoFocus
        />
        <div className="flex gap-2 mt-4">
          <Button variant="secondary" className="flex-1" onClick={() => setPendingImport(null)}>取消</Button>
          <Button className="flex-1" onClick={confirmImport}>开始导入</Button>
        </div>
      </Sheet>
    </div>
  );
}
