/**
 * CitationLink — source, timestamp and accessibility state (plan §4.7 / §7.8)
 *
 * Opens the original platform URL when available; otherwise opens the
 * in-app transcript with a timestamp. Never fabricates a play URL.
 */

import { useState } from 'react';
import { LinkIcon, DocumentTextIcon } from '@heroicons/react/24/outline';

export interface Citation {
  chunk_id: string;
  quote?: string | null;
  title?: string;
  original_url?: string | null;
  start_ms?: number | null;
  end_ms?: number | null;
  accessible?: boolean;
}

export function formatTimestamp(ms: number | null | undefined): string {
  if (ms === null || ms === undefined) return '';
  const totalSeconds = Math.floor(ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
}

export function CitationLink({ citation }: { citation: Citation }) {
  const [expanded, setExpanded] = useState(false);
  const timestamp = formatTimestamp(citation.start_ms);

  return (
    <span className="inline-block">
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="inline-flex items-center gap-1 text-xs text-primary-700 bg-primary-50 border border-primary-100 rounded-full px-2 py-0.5 hover:bg-primary-100"
      >
        {citation.original_url ? <LinkIcon className="w-3 h-3" /> : <DocumentTextIcon className="w-3 h-3" />}
        {citation.title || '来源'}
        {timestamp && <span className="text-primary-500">· {timestamp}</span>}
        {!citation.accessible && citation.accessible !== undefined && (
          <span className="text-gray-400">· 来源不可用</span>
        )}
      </button>

      {expanded && (
        <span className="block mt-1 text-xs text-gray-500 bg-gray-50 border border-gray-100 rounded-lg p-2 max-w-md">
          {citation.original_url ? (
            <a
              href={citation.original_url}
              target="_blank"
              rel="noreferrer"
              className="text-primary-600 underline break-all"
            >
              打开原始链接{timestamp ? `（定位 ${timestamp}）` : ''}
            </a>
          ) : (
            <span>原视频不在云端，查看应用内字幕{timestamp ? `（${timestamp}）` : ''}</span>
          )}
          {citation.quote && (
            <span className="block mt-1 text-gray-600 border-l-2 border-primary-200 pl-2">
              “{citation.quote}”
            </span>
          )}
        </span>
      )}
    </span>
  );
}
