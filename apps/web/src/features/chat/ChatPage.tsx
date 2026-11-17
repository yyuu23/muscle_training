/**
 * Coach chat page (plan §8.1 教练对话页): validated answers with
 * citations, pending memory candidates, missing-field prompts.
 * Bubble layout + typing indicator + entrance animations.
 */

import { useEffect, useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { PaperAirplaneIcon, ChatBubbleLeftRightIcon, ShieldCheckIcon } from '@heroicons/react/24/solid';
import { apiGet, apiPost } from '../../api/client';
import type { components } from '../../api/generated/schema';
import { CitationLink } from '../../components/CitationLink';
import { useAuth } from '../auth/useAuth';
import { EmptyState } from '../../components/ErrorState';

type Schemas = components['schemas'];
type CoachResponse = Schemas['CoachResponseOut'];

interface ChatMessageLocal {
  role: 'user' | 'assistant';
  content: string;
  citations?: CoachResponse['citations'];
  status?: CoachResponse['status'];
}

const STATUS_HINTS: Record<string, string> = {
  needs_input: '需要补充信息',
  draft_ready: '已生成草稿，请到记录页确认',
  unable_to_answer: '暂时无法回答',
};

const SUGGESTIONS = [
  '帮我看看卧推的动作要点',
  '昨天做了3组深蹲每组10个',
  '这周练得怎么样',
];

function TypingDots() {
  return (
    <div className="flex items-center gap-1.5 pl-1 py-1" aria-label="教练思考中">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="w-2 h-2 rounded-full bg-primary animate-typing"
          style={{ animationDelay: `${i * 0.18}s` }}
        />
      ))}
      <span className="text-xs text-text-muted ml-1">教练思考中…</span>
    </div>
  );
}

export function ChatPage() {
  const { capabilities } = useAuth();
  const queryClient = useQueryClient();
  const [messages, setMessages] = useState<ChatMessageLocal[]>([]);
  const [input, setInput] = useState('');
  const bottomRef = useRef<HTMLDivElement>(null);

  const candidatesQuery = useQuery({
    queryKey: ['memory-candidates'],
    queryFn: () => apiGet('/api/v1/profiles/memory-candidates'),
  });

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages.length]);

  const send = useMutation({
    mutationFn: (message: string) =>
      apiPost('/api/v1/chat', { message }),
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
      if ((response.memory_candidate_ids?.length ?? 0) > 0) {
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
      apiPost('/api/v1/profiles/memory-candidates/{candidate_id}/resolve', { decision }, { candidate_id: id }),
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
    <div className="flex flex-col h-[calc(100vh-4rem)] lg:h-[calc(100vh-3rem)] w-full max-w-2xl lg:max-w-3xl mx-auto px-4 py-4">
      <h1 className="text-2xl font-bold text-text mb-3 flex items-center gap-2">
        <ChatBubbleLeftRightIcon className="w-6 h-6 text-primary" /> 教练
      </h1>

      {modelUnavailable && (
        <div className="card !py-2.5 mb-3 text-xs text-text-secondary !bg-surface-2 animate-fade-in">
          模型功能未配置；训练记录、查看与同步不受影响。
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-4 pb-4 scrollbar-thin">
        {messages.length === 0 && (
          <div className="card p-6">
            <EmptyState
              title="问你的教练"
              description="回答基于你的档案与知识库资料，附带可溯源引用"
            />
            <div className="flex flex-wrap gap-2 justify-center mt-2">
              {SUGGESTIONS.map((s, i) => (
                <button
                  key={s}
                  onClick={() => {
                    if (modelUnavailable || send.isPending) return;
                    setMessages((prev) => [...prev, { role: 'user', content: s }]);
                    send.mutate(s);
                  }}
                  className="badge badge-primary cursor-pointer hover:shadow-soft transition-shadow animate-fade-in"
                  style={{ animationDelay: `${i * 80}ms` }}
                  disabled={modelUnavailable}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((message, i) => (
          <div
            key={i}
            className={`flex animate-slide-up ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
            style={{ animationDelay: `${Math.min(i, 6) * 40}ms` }}
          >
            <div
              className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                message.role === 'user'
                  ? 'bg-primary text-primary-contrast rounded-br-md shadow-soft'
                  : 'bg-surface border border-border-default text-text rounded-bl-md shadow-soft'
              }`}
            >
              <p className="whitespace-pre-wrap">{message.content}</p>

              {message.status && message.status !== 'answered' && (
                <p className={`text-xs mt-2 ${message.role === 'user' ? 'opacity-70' : 'text-warning'}`}>
                  · {STATUS_HINTS[message.status]}
                </p>
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

        {send.isPending && <TypingDots />}
        <div ref={bottomRef} />
      </div>

      {/* Memory candidates inline */}
      {candidatesQuery.data && candidatesQuery.data.length > 0 && (
        <div className="card !p-3.5 mb-3 text-xs space-y-2 animate-slide-up">
          <p className="text-text-secondary">教练记住了这些候选信息，需要你确认：</p>
          {candidatesQuery.data.slice(0, 3).map((c) => (
            <div key={c.id} className="flex items-center justify-between gap-2">
              <span className="text-text flex-1 truncate">{c.proposed_fact}</span>
              <button
                onClick={() => resolve.mutate({ id: c.id, decision: 'accept' })}
                className="text-primary font-semibold shrink-0 hover:underline"
              >
                确认
              </button>
              <button
                onClick={() => resolve.mutate({ id: c.id, decision: 'reject' })}
                className="text-text-muted shrink-0 hover:text-text"
              >
                忽略
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Input */}
      <div className="flex gap-2 pb-1">
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
          className="btn btn-primary !px-4 !rounded-xl"
          aria-label="发送"
        >
          <PaperAirplaneIcon className="w-5 h-5" />
        </button>
      </div>
      <p className="text-[10px] text-text-muted/80 text-center pb-2 flex items-center justify-center gap-1">
        <ShieldCheckIcon className="w-3 h-3" />
        回答会引用你的知识库资料；教练不能直接修改你的计划或记录
      </p>
    </div>
  );
}
