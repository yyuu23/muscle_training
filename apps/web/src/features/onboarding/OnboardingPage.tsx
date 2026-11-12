/**
 * Onboarding wizard (plan §8.1: 建档页)
 *
 * Steps: goal → experience → schedule → weekdays → equipment → load
 * increments. Missing-field hints come from GET /profiles/completeness.
 */

import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { CheckCircleIcon } from '@heroicons/react/24/outline';
import { apiFetch, APIError } from '../../api/client';
import { db } from '../../offline/database';
import { useAuth } from '../auth/useAuth';

interface OnboardingForm {
  goal: string;
  training_experience_months: number;
  sessions_per_week: number;
  minutes_per_session: number;
  available_weekdays: number[];
  equipment: string[];
  available_load_increments: string[];
}

const GOALS = ['力量提升', '增肌', '保持健康', '改善体态'];
const EQUIPMENT_OPTIONS = ['barbell', 'dumbbell', 'bench', 'pull-up-bar', 'kettlebell', 'band', 'bodyweight'];
const EQUIPMENT_LABELS: Record<string, string> = {
  barbell: '杠铃', dumbbell: '哑铃', bench: '卧推凳', 'pull-up-bar': '单杠',
  kettlebell: '壶铃', band: '弹力带', bodyweight: '自重',
};
const WEEKDAY_LABELS = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'];
const INCREMENT_OPTIONS = ['1.25', '2.5', '5'];

const STEPS = ['目标', '经验', '频率', '时间', '器械', '增量'] as const;

export function OnboardingPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const [step, setStep] = useState(0);

  const { data: profileData } = useQuery({
    queryKey: ['profiles', 'me'],
    queryFn: () => apiFetch<{ profile: { version: number } & Partial<OnboardingForm> }>('/profiles'),
  });

  const { data: completeness } = useQuery({
    queryKey: ['profiles', 'completeness'],
    queryFn: () => apiFetch<{ missing_fields: string[]; complete: boolean }>('/profiles/completeness'),
  });

  const { register, handleSubmit, watch, setValue, getValues } = useForm<OnboardingForm>({
    defaultValues: {
      goal: '',
      training_experience_months: 6,
      sessions_per_week: 3,
      minutes_per_session: 60,
      available_weekdays: [1, 3, 5],
      equipment: [],
      available_load_increments: ['2.5'],
    },
  });

  // Pre-fill from the server profile
  useEffect(() => {
    if (profileData?.profile) {
      const p = profileData.profile;
      if (p.goal) setValue('goal', p.goal);
      if (p.training_experience_months != null) setValue('training_experience_months', p.training_experience_months);
      if (p.sessions_per_week != null) setValue('sessions_per_week', p.sessions_per_week);
      if (p.minutes_per_session != null) setValue('minutes_per_session', p.minutes_per_session);
      if (p.available_weekdays) setValue('available_weekdays', p.available_weekdays);
      if (p.equipment) setValue('equipment', p.equipment);
      if (p.available_load_increments) setValue('available_load_increments', p.available_load_increments);
    }
  }, [profileData, setValue]);

  // Already complete → straight to today
  useEffect(() => {
    if (completeness?.complete) {
      navigate('/today', { replace: true });
    }
  }, [completeness, navigate]);

  const missingHint = useMemo(() => {
    if (!completeness?.missing_fields?.length) return null;
    const labels: Record<string, string> = {
      goal: '训练目标', training_experience_months: '训练经验',
      sessions_per_week: '每周次数', minutes_per_session: '单次时长', equipment: '可用器械',
    };
    return completeness.missing_fields.map((f) => labels[f] ?? f).join('、');
  }, [completeness]);

  const selectedWeekdays = watch('available_weekdays');
  const selectedEquipment = watch('equipment');
  const selectedIncrements = watch('available_load_increments');

  const toggle = (field: 'available_weekdays' | 'equipment' | 'available_load_increments', value: string | number) => {
    const current = getValues(field) as (string | number)[];
    const next = current.includes(value)
      ? current.filter((v) => v !== value)
      : [...current, value];
    setValue(field, next as never);
  };

  const submit = handleSubmit(async (data) => {
    const version = profileData?.profile?.version ?? 1;
    try {
      const updated = await apiFetch<{ version: number }>('/profiles', {
        method: 'PATCH',
        body: { expected_version: version, ...data },
      });
      // Update the local snapshot cache
      if (user) {
        const local = await db.profiles.get(`profile-${user.id}`);
        await db.profiles.put({
          id: `profile-${user.id}`,
          owner_user_id: user.id,
          version: updated.version,
          goal: data.goal,
          height_cm: local?.height_cm ?? null,
          training_experience_months: data.training_experience_months,
          sessions_per_week: data.sessions_per_week,
          minutes_per_session: data.minutes_per_session,
          available_weekdays: data.available_weekdays,
          equipment: data.equipment,
          available_load_increments: data.available_load_increments,
        });
      }
      await queryClient.invalidateQueries({ queryKey: ['profiles'] });
      navigate('/today');
    } catch (err) {
      if (err instanceof APIError && err.code === 'VERSION_CONFLICT') {
        alert('档案已被其他设备修改，正在刷新…');
        await queryClient.invalidateQueries({ queryKey: ['profiles'] });
      } else {
        alert(err instanceof Error ? err.message : '保存失败');
      }
    }
  });

  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4">
      <div className="max-w-lg mx-auto">
        <h1 className="text-2xl font-bold text-gray-900 mb-1">建立训练档案</h1>
        <p className="text-sm text-gray-500 mb-6">
          {missingHint ? `还缺少：${missingHint}` : '这些信息用于生成适合你的训练计划'}
        </p>

        {/* Progress */}
        <div className="flex gap-1 mb-6">
          {STEPS.map((label, i) => (
            <div key={label} className="flex-1">
              <div className={`h-1.5 rounded-full ${i <= step ? 'bg-primary-600' : 'bg-gray-200'}`} />
              <p className={`text-[10px] mt-1 text-center ${i <= step ? 'text-primary-700' : 'text-gray-400'}`}>
                {label}
              </p>
            </div>
          ))}
        </div>

        <form onSubmit={submit} className="card p-6 space-y-6">
          {step === 0 && (
            <div>
              <h2 className="font-semibold mb-3">你的训练目标是什么？</h2>
              <div className="grid grid-cols-2 gap-2">
                {GOALS.map((goal) => (
                  <button
                    key={goal}
                    type="button"
                    onClick={() => setValue('goal', goal)}
                    className={`p-3 rounded-xl border text-sm ${
                      watch('goal') === goal
                        ? 'border-primary-500 bg-primary-50 text-primary-700'
                        : 'border-gray-200 text-gray-600'
                    }`}
                  >
                    {goal}
                  </button>
                ))}
              </div>
              {!watch('goal') && <p className="text-xs text-amber-600 mt-2">请选择一个目标</p>}
            </div>
          )}

          {step === 1 && (
            <div>
              <h2 className="font-semibold mb-3">系统训练了多久？（月）</h2>
              <input
                type="range"
                min={0}
                max={120}
                step={1}
                {...register('training_experience_months', { valueAsNumber: true })}
                className="w-full accent-primary-600"
              />
              <p className="text-center text-lg font-semibold text-primary-700 mt-2">
                {watch('training_experience_months')} 个月
              </p>
            </div>
          )}

          {step === 2 && (
            <div className="space-y-6">
              <div>
                <h2 className="font-semibold mb-3">每周训练几天？</h2>
                <div className="flex gap-2">
                  {[2, 3, 4, 5].map((n) => (
                    <button
                      key={n}
                      type="button"
                      onClick={() => setValue('sessions_per_week', n)}
                      className={`flex-1 py-3 rounded-xl border text-center ${
                        watch('sessions_per_week') === n
                          ? 'border-primary-500 bg-primary-50 text-primary-700 font-semibold'
                          : 'border-gray-200 text-gray-600'
                      }`}
                    >
                      {n} 天
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <h2 className="font-semibold mb-3">每次多久？</h2>
                <div className="flex gap-2">
                  {[30, 45, 60, 90].map((n) => (
                    <button
                      key={n}
                      type="button"
                      onClick={() => setValue('minutes_per_session', n)}
                      className={`flex-1 py-3 rounded-xl border text-center text-sm ${
                        watch('minutes_per_session') === n
                          ? 'border-primary-500 bg-primary-50 text-primary-700 font-semibold'
                          : 'border-gray-200 text-gray-600'
                      }`}
                    >
                      {n} 分钟
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {step === 3 && (
            <div>
              <h2 className="font-semibold mb-3">哪些天可以训练？</h2>
              <div className="grid grid-cols-4 gap-2">
                {WEEKDAY_LABELS.map((label, i) => {
                  const weekday = i + 1;
                  const active = selectedWeekdays.includes(weekday);
                  return (
                    <button
                      key={label}
                      type="button"
                      onClick={() => toggle('available_weekdays', weekday)}
                      className={`py-3 rounded-xl border text-sm ${
                        active
                          ? 'border-primary-500 bg-primary-50 text-primary-700 font-semibold'
                          : 'border-gray-200 text-gray-600'
                      }`}
                    >
                      {label}
                    </button>
                  );
                })}
              </div>
              {selectedWeekdays.length !== watch('sessions_per_week') && (
                <p className="text-xs text-amber-600 mt-2">
                  已选 {selectedWeekdays.length} 天，与计划的每周 {watch('sessions_per_week')} 天
                  {selectedWeekdays.length > watch('sessions_per_week') ? '（多于计划天数也可以）' : '（不足）'}
                </p>
              )}
            </div>
          )}

          {step === 4 && (
            <div>
              <h2 className="font-semibold mb-3">有哪些器械？</h2>
              <div className="grid grid-cols-2 gap-2">
                {EQUIPMENT_OPTIONS.map((eq) => {
                  const active = selectedEquipment.includes(eq);
                  return (
                    <button
                      key={eq}
                      type="button"
                      onClick={() => toggle('equipment', eq)}
                      className={`p-3 rounded-xl border text-sm flex items-center justify-between ${
                        active
                          ? 'border-primary-500 bg-primary-50 text-primary-700'
                          : 'border-gray-200 text-gray-600'
                      }`}
                    >
                      {EQUIPMENT_LABELS[eq]}
                      {active && <CheckCircleIcon className="w-4 h-4 text-primary-500" />}
                    </button>
                  );
                })}
              </div>
              {selectedEquipment.length === 0 && (
                <p className="text-xs text-amber-600 mt-2">至少选择「自重」或一种器械</p>
              )}
            </div>
          )}

          {step === 5 && (
            <div>
              <h2 className="font-semibold mb-3">杠铃片/哑铃的最小增量？</h2>
              <div className="flex gap-2">
                {INCREMENT_OPTIONS.map((inc) => {
                  const active = selectedIncrements.includes(inc);
                  return (
                    <button
                      key={inc}
                      type="button"
                      onClick={() => toggle('available_load_increments', inc)}
                      className={`flex-1 py-3 rounded-xl border text-sm ${
                        active
                          ? 'border-primary-500 bg-primary-50 text-primary-700 font-semibold'
                          : 'border-gray-200 text-gray-600'
                      }`}
                    >
                      {inc} kg
                    </button>
                  );
                })}
              </div>
              <p className="text-xs text-gray-400 mt-2">用于判断能否安全加重（如两侧各加 1.25kg）</p>
            </div>
          )}

          <div className="flex justify-between pt-2">
            <button
              type="button"
              onClick={() => setStep((s) => Math.max(0, s - 1))}
              disabled={step === 0}
              className="px-4 py-2 text-sm text-gray-500 disabled:invisible"
            >
              上一步
            </button>
            {step < STEPS.length - 1 ? (
              <button
                type="button"
                onClick={() => setStep((s) => s + 1)}
                className="btn-primary px-6 py-2 text-sm"
              >
                下一步
              </button>
            ) : (
              <button type="submit" className="btn-primary px-6 py-2 text-sm">
                完成建档
              </button>
            )}
          </div>
        </form>
      </div>
    </div>
  );
}
