import { createBrowserRouter, Navigate } from 'react-router-dom';
import { lazy, Suspense } from 'react';
import { AppShell } from './AppShell';

// Auth pages
const LoginPage = lazy(() => import('../features/auth/LoginPage').then((m) => ({ default: m.LoginPage })));
const RegisterPage = lazy(() => import('../features/auth/RegisterPage').then((m) => ({ default: m.RegisterPage })));

// Main pages
const TodayPage = lazy(() => import('../features/today/TodayPage').then((m) => ({ default: m.TodayPage })));
const OnboardingPage = lazy(() => import('../features/onboarding/OnboardingPage').then((m) => ({ default: m.OnboardingPage })));
const SessionPage = lazy(() => import('../features/workouts/SessionPage').then((m) => ({ default: m.SessionPage })));
const HistoryPage = lazy(() => import('../features/history/HistoryPage').then((m) => ({ default: m.HistoryPage })));
const PlansPage = lazy(() => import('../features/plans/PlansPage').then((m) => ({ default: m.PlansPage })));
const PlanDetailPage = lazy(() => import('../features/plans/PlanDetailPage').then((m) => ({ default: m.PlanDetailPage })));
const ChatPage = lazy(() => import('../features/chat/ChatPage').then((m) => ({ default: m.ChatPage })));
const NutritionPage = lazy(() => import('../features/nutrition/NutritionPage').then((m) => ({ default: m.NutritionPage })));
const KnowledgePage = lazy(() => import('../features/knowledge/KnowledgePage').then((m) => ({ default: m.KnowledgePage })));
const ReviewsPage = lazy(() => import('../features/reviews/ReviewsPage').then((m) => ({ default: m.ReviewsPage })));
const SettingsPage = lazy(() => import('../features/settings/SettingsPage').then((m) => ({ default: m.SettingsPage })));
const AdminCatalogPage = lazy(() => import('../features/admin/AdminCatalogPage').then((m) => ({ default: m.AdminCatalogPage })));

const PageLoader = () => (
  <div className="min-h-screen flex items-center justify-center">
    <div className="text-gray-600">加载中...</div>
  </div>
);

const page = (element: React.ReactNode) => (
  <Suspense fallback={<PageLoader />}>{element}</Suspense>
);

export const router = createBrowserRouter([
  {
    path: '/login',
    element: page(<LoginPage />),
  },
  {
    path: '/register',
    element: page(<RegisterPage />),
  },
  {
    path: '/',
    element: <AppShell />,
    children: [
      { index: true, element: <Navigate to="/today" replace /> },
      { path: 'today', element: page(<TodayPage />) },
      { path: 'onboarding', element: page(<OnboardingPage />) },
      { path: 'workouts/:id', element: page(<SessionPage />) },
      { path: 'history', element: page(<HistoryPage />) },
      { path: 'plans', element: page(<PlansPage />) },
      { path: 'plans/:planId', element: page(<PlanDetailPage />) },
      { path: 'chat', element: page(<ChatPage />) },
      { path: 'nutrition', element: page(<NutritionPage />) },
      { path: 'knowledge', element: page(<KnowledgePage />) },
      { path: 'reviews', element: page(<ReviewsPage />) },
      { path: 'settings', element: page(<SettingsPage />) },
      { path: 'admin/catalog', element: page(<AdminCatalogPage />) },
    ],
  },
]);
