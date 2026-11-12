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

export function NutritionPage() {
  const { user } = useAuth();
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
  };

  return (
    <div className="max-w-2xl mx-auto px-4 py-6 space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">饮食与体重</h1>

      {/* Weight */}
      <div className="card p-5">
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-semibold flex items-center gap-2">
            <ScaleIcon className="w-5 h-5 text-primary-600" /> 体重记录
          </h2>
          {latestWeight && (
            <span className="text-sm text-gray-500">
              最近 {latestWeight.value} kg · {new Date(latestWeight.observed_at).toLocaleDateString('zh-CN')}
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
            className="input flex-1"
          />
          <button onClick={saveWeight} disabled={!weight} className="btn-primary px-5 text-sm">
            记录
          </button>
        </div>
      </div>

      {/* Meal quick log */}
      <div className="card p-5">
        <h2 className="font-semibold mb-3">记录一餐</h2>
        <div className="space-y-3">
          <div className="flex gap-2">
            {MEAL_TYPES.map((t) => (
              <button
                key={t.value}
                onClick={() => setMealType(t.value)}
                className={`flex-1 py-2 rounded-lg border text-sm ${
                  mealType === t.value
                    ? 'border-primary-500 bg-primary-50 text-primary-700 font-medium'
                    : 'border-gray-200 text-gray-600'
                }`}
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
            className="input w-full"
          />
          <div className="flex items-center gap-2 text-sm">
            <span className="text-gray-500">营养来源：</span>
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
          <button onClick={saveMeal} disabled={!description.trim()} className="btn-primary w-full py-2.5 text-sm">
            保存（离线可用，联网后同步）
          </button>
        </div>
      </div>

      {/* Today's meals */}
      <div className="card p-5">
        <h2 className="font-semibold mb-3">今日记录</h2>
        {todayMeals.length === 0 ? (
          <EmptyState title="今天还没有饮食记录" />
        ) : (
          <ul className="divide-y divide-gray-50">
            {todayMeals.map((meal) => (
              <li key={meal.id} className="py-3 flex items-start justify-between gap-3">
                <div>
                  <p className="text-sm text-gray-800">{meal.description}</p>
                  <p className="text-xs text-gray-400 mt-0.5">
                    {new Date(meal.occurred_at).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}
                    {meal.meal_type && ` · ${MEAL_TYPES.find((t) => t.value === meal.meal_type)?.label ?? meal.meal_type}`}
                  </p>
                </div>
                <span className="text-xs bg-gray-50 text-gray-500 px-2 py-1 rounded-full shrink-0">
                  {SOURCE_LABELS[meal.nutrition_source] ?? meal.nutrition_source}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
