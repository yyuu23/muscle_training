/**
 * Coach chat page (plan §8.1 教练对话页): validated answers with
 * citations, pending memory candidates, missing-field prompts.
 */

import { useEffect, useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { PaperAirplaneIcon, ChatBubbleLeftRightIcon } from '@heroicons/react/24/outline';
import { apiFetch } from '../../api/client';
import { CitationLink } from '../../components/CitationLink';
import { useAuth } from '../auth/useAuth';
import { EmptyState } from '../../components/ErrorState';

interface CoachResponse {
  status: 'answered' | 'needs_input' | 'draft_ready' | 'unable_to_answer';
  answer_markdown: string;
  citations: { chunk_id: string; quote?: string | null }[];
  missing_fields: string[];
  memory_candidate_ids: string[];
  conversation_id: string | null;
  data_cutoff_at: string | null;
}

interface ChatMessageLocal {
  role: 'user' | 'assistant';
  content: string;
  citations?: CoachResponse['citations'];
  status?: CoachResponse['status'];
}

interface MemoryCandidate {
  id: string;
  proposed_fact: string;
  source_kind: string;
}

const STATUS_HINTS: Record<string, string> = {
  needs_input: '需要补充信息',
  draft_ready: '已生成草稿，请到记录页确认',
  unable_to_answer: '暂时无法回答',
};

export function ChatPage() {
  const { capabilities } = useAuth();
  const queryClient = useQueryClient();
  const [messages, setMessages] = useState<ChatMessageLocal[]>([]);
  const [input, setInput] = useState('');
  const bottomRef = useRef<HTMLDivElement>(null);

  const candidatesQuery = useQuery({
    queryKey: ['memory-candidates'],
    queryFn: () => apiFetch<MemoryCandidate[]>('/profiles/memory-candidates'),
  });

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages.length]);

  const send = useMutation({
    mutationFn: (message: string) =>
      apiFetch<CoachResponse>('/chat', { method: 'POST', body: { message } }),
    onSuccess: (response) => {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: response.answer_markdown,
          citations: response.citations,
          status: response.status,
        },
      ]);
      if (response.memory_candidate_ids.length > 0) {
        void queryClient.invalidateQueries({ queryKey: ['memory-candidates'] });
      }
    },
    onError: (err) => {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: err instanceof Error ? err.message : '请求失败，请重试', status: 'unable_to_answer' },
      ]);
    },
  });

  const resolve = useMutation({
    mutationFn: ({ id, decision }: { id: string; decision: 'accept' | 'reject' }) =>
      apiFetch(`/profiles/memory-candidates/${id}/resolve`, { method: 'POST', body: { decision } }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['memory-candidates'] }),
  });

  const submit = () => {
    const message = input.trim();
    if (!message || send.isPending) return;
    setMessages((prev) => [...prev, { role: 'user', content: message }]);
    setInput('');
    send.mutate(message);
  };

  const modelUnavailable = capabilities !== null && !capabilities.chat_model_configured;

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)] max-w-2xl mx-auto px-4 py-4">
      <h1 className="text-2xl font-bold text-gray-900 mb-3 flex items-center gap-2">
        <ChatBubbleLeftRightIcon className="w-6 h-6 text-primary-600" /> 教练
      </h1>

      {modelUnavailable && (
        <div className="card p-3 mb-3 text-xs text-gray-500 bg-gray-50">
          模型功能未配置；训练记录、查看与同步不受影响。
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-4 pb-4">
        {messages.length === 0 && (
          <div className="card p-6">
            <EmptyState
              title="问你的教练"
              description="例如：帮我看看卧推的动作要点 / 昨天做了3组深蹲每组10个 / 这周练得怎么样"
            />
          </div>
        )}

        {messages.map((message, i) => (
          <div key={i} className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div
              className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm ${
                message.role === 'user'
                  ? 'bg-primary-600 text-white rounded-br-md'
                  : 'bg-white border border-gray-100 text-gray-800 rounded-bl-md'
              }`}
            >
              <p className="whitespace-pre-wrap">{message.content}</p>

              {message.status && message.status !== 'answered' && (
                <p className="text-xs mt-2 opacity-70">· {STATUS_HINTS[message.status]}</p>
              )}

              {message.citations && message.citations.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1">
                  {message.citations.map((c, j) => (
                    <CitationLink key={j} citation={{ chunk_id: c.chunk_id, quote: c.quote }} />
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}

        {send.isPending && (
          <div className="text-sm text-gray-400 animate-pulse pl-1">教练思考中…</div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Memory candidates inline */}
      {candidatesQuery.data && candidatesQuery.data.length > 0 && (
        <div className="card p-3 mb-3 text-xs space-y-2">
          <p className="text-gray-500">教练记住了这些候选信息，需要你确认：</p>
          {candidatesQuery.data.slice(0, 3).map((c) => (
            <div key={c.id} className="flex items-center justify-between gap-2">
              <span className="text-gray-700 flex-1 truncate">{c.proposed_fact}</span>
              <button
                onClick={() => resolve.mutate({ id: c.id, decision: 'accept' })}
                className="text-primary-600 font-medium shrink-0"
              >
                确认
              </button>
              <button
                onClick={() => resolve.mutate({ id: c.id, decision: 'reject' })}
                className="text-gray-400 shrink-0"
              >
                忽略
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Input */}
      <div className="flex gap-2 pb-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.nativeEvent.isComposing) submit();
          }}
          placeholder={modelUnavailable ? '模型未配置，仅可浏览' : '输入问题或描述训练…'}
          disabled={modelUnavailable || send.isPending}
          className="input flex-1"
        />
        <button
          onClick={submit}
          disabled={!input.trim() || send.isPending || modelUnavailable}
          className="btn-primary px-4 rounded-xl"
          aria-label="发送"
        >
          <PaperAirplaneIcon className="w-5 h-5" />
        </button>
      </div>
      <p className="text-[10px] text-gray-300 text-center pb-2">
        回答会引用你的知识库资料；教练不能直接修改你的计划或记录
      </p>
    </div>
  );
}
