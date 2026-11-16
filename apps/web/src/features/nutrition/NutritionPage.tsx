/**
 * Nutrition page (plan §8.1 饮食页): quick meal + weight logging with
 * estimate-source labels. All writes go through the outbox (offline ok).
 */

import { useState } from 'react';
import { useLiveQuery } from 'dexie-react-hooks';
import { ScaleIcon } from '@heroicons/react/24/outline';
import { db } from '../../offline/database';
import { outboxService } from '../../offline/outbox';
import { useAuth } from '../auth/useAuth';
import { EmptyState } from '../../components/ErrorState';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { useToast } from '../../components/ui/Toast';

const MEAL_TYPES = [
  { value: 'breakfast', label: '早餐' },
  { value: 'lunch', label: '午餐' },
  { value: 'dinner', label: '晚餐' },
  { value: 'snack', label: '加餐' },
] as const;

const SOURCE_LABELS: Record<string, string> = {
  user_label: '自报分量',
  user_estimate: '自行估计',
  model_estimate: '模型估计',
  unknown: '未标注',
};

const CHIP_ACTIVE = 'border-primary bg-primary-soft text-primary font-semibold';
const CHIP_IDLE = 'border-border-default text-text-secondary hover:border-border-strong';

export function NutritionPage() {
  const { user } = useAuth();
  const toast = useToast();
  const userId = user?.id ?? '';

  const meals = useLiveQuery(
    () =>
      db.mealLogs
        .where('owner_user_id')
        .equals(userId)
        .reverse()
        .sortBy('occurred_at'),
    [userId],
  );

  const measurements = useLiveQuery(
    () =>
      db.measurements
        .where('owner_user_id')
        .equals(userId)
        .reverse()
        .sortBy('observed_at'),
    [userId],
  );

  const [mealType, setMealType] = useState<string>('breakfast');
  const [description, setDescription] = useState('');
  const [nutritionSource, setNutritionSource] = useState<string>('user_estimate');
  const [weight, setWeight] = useState('');

  const today = new Date().toISOString().slice(0, 10);
  const todayMeals = (meals ?? []).filter((m) => m.occurred_at.slice(0, 10) === today);
  const latestWeight = (measurements ?? []).find((m) => m.measurement_type === 'weight');

  const saveMeal = async () => {
    if (!description.trim() || !userId) return;
    await outboxService.mealCreated(userId, {
      id: crypto.randomUUID(),
      occurred_at: new Date().toISOString(),
      meal_type: mealType as 'breakfast',
      description: description.trim(),
      nutrition_source: nutritionSource as 'user_estimate',
    });
    setDescription('');
    toast.show('已记录一餐');
  };

  const saveWeight = async () => {
    const value = parseFloat(weight);
    if (!value || value <= 0 || value > 400 || !userId) return;
    await outboxService.measurementCreated(userId, {
      id: crypto.randomUUID(),
      measurement_type: 'weight',
      value: value.toFixed(2),
      unit: 'kg',
      observed_at: new Date().toISOString(),
    });
    setWeight('');
    toast.show(`已记录体重 ${value.toFixed(1)} kg`);
  };

  return (
    <div className="page-container py-6 space-y-5">
      <h1 className="text-2xl font-bold text-text">饮食与体重</h1>

      <div className="lg:grid lg:grid-cols-2 lg:gap-5 lg:items-start space-y-5 lg:space-y-0">

      {/* Weight */}
      <div className="card p-5 animate-slide-up">
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-semibold flex items-center gap-2">
            <ScaleIcon className="w-5 h-5 text-primary" /> 体重记录
          </h2>
          {latestWeight && (
            <span className="text-sm text-text-secondary tabular-nums animate-count-pop" key={latestWeight.value}>
              最近 <b className="text-text">{latestWeight.value}</b> kg · {new Date(latestWeight.observed_at).toLocaleDateString('zh-CN')}
            </span>
          )}
        </div>
        <div className="flex gap-2">
          <input
            type="number"
            inputMode="decimal"
            step="0.1"
            min="20"
            max="400"
            placeholder="今日体重 (kg)"
            value={weight}
            onChange={(e) => setWeight(e.target.value)}
            className="input flex-1 tabular-nums"
          />
          <Button onClick={saveWeight} disabled={!weight}>记录</Button>
        </div>
      </div>

      {/* Meal quick log */}
      <div className="card p-5 animate-slide-up" style={{ animationDelay: '60ms' }}>
        <h2 className="font-semibold mb-3">记录一餐</h2>
        <div className="space-y-3">
          <div className="flex gap-2">
            {MEAL_TYPES.map((t) => (
              <button
                key={t.value}
                onClick={() => setMealType(t.value)}
                className={`flex-1 py-2.5 rounded-xl border text-sm transition-all ${mealType === t.value ? CHIP_ACTIVE : CHIP_IDLE}`}
              >
                {t.label}
              </button>
            ))}
          </div>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="吃了什么，大约多少（如：鸡胸肉150g、米饭一碗）"
            rows={2}
            className="input"
          />
          <div className="flex items-center gap-2 text-sm">
            <span className="text-text-secondary shrink-0">营养来源：</span>
            <select
              value={nutritionSource}
              onChange={(e) => setNutritionSource(e.target.value)}
              className="input flex-1"
            >
              <option value="user_estimate">自行估计</option>
              <option value="user_label">自报分量</option>
              <option value="unknown">不标注</option>
            </select>
          </div>
          <Button className="w-full" onClick={saveMeal} disabled={!description.trim()}>
            保存（离线可用，联网后同步）
          </Button>
        </div>
      </div>

      </div>

      {/* Today's meals */}
      <div className="card p-5 animate-slide-up" style={{ animationDelay: '120ms' }}>
        <h2 className="font-semibold mb-3">今日记录</h2>
        {todayMeals.length === 0 ? (
          <EmptyState title="今天还没有饮食记录" />
        ) : (
          <ul className="divide-y divide-border-default/60 -mx-2">
            {todayMeals.map((meal, i) => (
              <li
                key={meal.id}
                className="py-3 px-2 flex items-start justify-between gap-3 animate-slide-up"
                style={{ animationDelay: `${i * 50}ms` }}
              >
                <div>
                  <p className="text-sm text-text">{meal.description}</p>
                  <p className="text-xs text-text-muted mt-0.5">
                    {new Date(meal.occurred_at).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}
                    {meal.meal_type && ` · ${MEAL_TYPES.find((t) => t.value === meal.meal_type)?.label ?? meal.meal_type}`}
                  </p>
                </div>
                <Badge tone="neutral" className="shrink-0">
                  {SOURCE_LABELS[meal.nutrition_source] ?? meal.nutrition_source}
                </Badge>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
