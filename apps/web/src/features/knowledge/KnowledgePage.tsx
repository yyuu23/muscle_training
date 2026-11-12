/**
 * Knowledge page (plan §8.1 知识库页): upload flow, import progress,
 * sources with status, chunks, temporary-file expiry, withdrawal.
 */

import { useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { DocumentArrowUpIcon } from '@heroicons/react/24/outline';
import { apiFetch, APIError } from '../../api/client';
import { EmptyState, ErrorState } from '../../components/ErrorState';

interface KnowledgeSource {
  id: string;
  title: string;
  source_type: string;
  status: 'processing' | 'awaiting_review' | 'indexing' | 'ready' | 'failed' | 'withdrawn';
  visibility: 'private' | 'shared';
  updated_at: string;
}

interface SourceDetail {
  source: KnowledgeSource;
  revisions: { id: string; revision: number; status: string; reviewed_at: string | null }[];
  chunks: { id: string; ordinal: number; start_ms: number | null; original_text: string }[];
}

const STATUS_LABELS: Record<string, string> = {
  processing: '处理中', awaiting_review: '待审核', indexing: '索引中',
  ready: '可用', failed: '失败', withdrawn: '已撤回',
};
const STATUS_STYLES: Record<string, string> = {
  processing: 'bg-blue-50 text-blue-600', awaiting_review: 'bg-amber-50 text-amber-700',
  indexing: 'bg-blue-50 text-blue-600', ready: 'bg-green-50 text-green-700',
  failed: 'bg-red-50 text-red-700', withdrawn: 'bg-gray-100 text-gray-400',
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

  const sourcesQuery = useQuery({
    queryKey: ['knowledge', 'sources'],
    queryFn: () => apiFetch<{ items: KnowledgeSource[] }>('/knowledge/sources'),
    refetchInterval: 8000,
  });

  const detailQuery = useQuery({
    queryKey: ['knowledge', detailId],
    queryFn: () => apiFetch<SourceDetail>(`/knowledge/sources/${detailId}`),
    enabled: !!detailId,
  });

  const withdraw = useMutation({
    mutationFn: (id: string) => apiFetch(`/knowledge/sources/${id}/withdraw`, { method: 'POST' }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['knowledge'] }),
  });

  const handleFile = async (file: File) => {
    setUploadError(null);
    setUploading(`正在上传 ${file.name}…`);
    try {
      const created = await apiFetch<{ asset_id: string; upload: { url: string; method: string; headers: Record<string, string> } }>(
        '/knowledge/assets/uploads',
        {
          method: 'POST',
          body: { filename: file.name, content_type: file.type || 'application/octet-stream', byte_size: file.size },
        },
      );

      // Development filesystem backend → upload through our API endpoint
      await apiFetch(`/assets/upload/${file.name}`, { method: 'PUT', rawBody: await file.arrayBuffer() }).catch(() => {});
      void created;

      const digest = await crypto.subtle.digest('SHA-256', await file.arrayBuffer());
      const sha256 = Array.from(new Uint8Array(digest)).map((b) => b.toString(16).padStart(2, '0')).join('');

      const completed = await apiFetch<{ verified: boolean; detail: string | null }>(
        `/knowledge/assets/${created.asset_id}/complete`,
        { method: 'POST', body: { sha256 } },
      );
      if (!completed.verified) {
        throw new Error(completed.detail ?? '上传校验失败');
      }

      const title = window.prompt('资料标题：', file.name.replace(/\.[^.]+$/, ''));
      if (!title) {
        setUploading(null);
        return;
      }

      await apiFetch('/knowledge/imports', {
        method: 'POST',
        body: { asset_id: created.asset_id, title },
      });
      setUploading('已提交导入任务，处理中…');
      await queryClient.invalidateQueries({ queryKey: ['knowledge'] });
      setTimeout(() => setUploading(null), 3000);
    } catch (err) {
      setUploadError(err instanceof APIError ? err.message : err instanceof Error ? err.message : '上传失败');
      setUploading(null);
    }
  };

  return (
    <div className="max-w-2xl mx-auto px-4 py-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">知识库</h1>
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
          <button
            onClick={() => fileInput.current?.click()}
            disabled={!!uploading}
            className="btn-primary px-4 py-2 text-sm inline-flex items-center gap-2"
          >
            <DocumentArrowUpIcon className="w-4 h-4" />
            上传资料
          </button>
        </>
      </div>

      <p className="text-xs text-gray-400">
        支持 TXT/Markdown/字幕(SRT/VTT)/音频/MP4。原视频与音频最多保留 7 天；转写与字幕长期保存。
        审核通过后才会用于教练回答。
      </p>

      {uploading && <div className="card p-3 text-sm text-gray-600">{uploading}</div>}
      {uploadError && <div className="card p-3 text-sm text-red-700 bg-red-50 border-red-100">{uploadError}</div>}

      {/* Sources */}
      {sourcesQuery.isLoading ? (
        <div className="card p-6 text-sm text-gray-400">加载中…</div>
      ) : sourcesQuery.isError ? (
        <ErrorState message="无法加载知识库" onRetry={() => void sourcesQuery.refetch()} />
      ) : sourcesQuery.data?.items.length ? (
        <ul className="space-y-2">
          {sourcesQuery.data.items.map((source) => (
            <li key={source.id} className="card p-4">
              <button className="w-full text-left" onClick={() => setDetailId(detailId === source.id ? null : source.id)}>
                <div className="flex items-center justify-between gap-2">
                  <span className="font-medium text-sm text-gray-900 truncate">{source.title}</span>
                  <span className={`text-xs px-2 py-0.5 rounded-full shrink-0 ${STATUS_STYLES[source.status]}`}>
                    {STATUS_LABELS[source.status]}
                  </span>
                </div>
                <p className="text-xs text-gray-400 mt-1">
                  {source.source_type === 'video' ? '视频' : source.source_type === 'audio' ? '音频'
                    : source.source_type === 'subtitle' ? '字幕' : '文档'}
                  {' · '}
                  {source.visibility === 'shared' ? '共享' : '私有'}
                  {' · '}
                  {new Date(source.updated_at).toLocaleDateString('zh-CN')}
                </p>
              </button>

              {detailId === source.id && (
                <div className="mt-3 border-t border-gray-50 pt-3 space-y-3">
                  {detailQuery.data ? (
                    <>
                      <div className="text-xs text-gray-500">
                        修订 {detailQuery.data.revisions.length} 个；片段 {detailQuery.data.chunks.length} 条
                      </div>
                      <div className="max-h-64 overflow-y-auto space-y-2">
                        {detailQuery.data.chunks.slice(0, 30).map((chunk) => (
                          <div key={chunk.id} className="bg-gray-50 rounded-lg p-2 text-xs">
                            {chunk.start_ms !== null && (
                              <span className="text-primary-600 font-mono mr-2">{formatMs(chunk.start_ms)}</span>
                            )}
                            <span className="text-gray-600 line-clamp-3">{chunk.original_text}</span>
                          </div>
                        ))}
                      </div>
                      {source.status === 'ready' && (
                        <button
                          onClick={() => withdraw.mutate(source.id)}
                          className="text-xs text-red-600 border border-red-100 rounded-lg px-3 py-1.5"
                        >
                          撤回（不再用于新回答）
                        </button>
                      )}
                    </>
                  ) : (
                    <p className="text-xs text-gray-400">加载详情…</p>
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
    </div>
  );
}
