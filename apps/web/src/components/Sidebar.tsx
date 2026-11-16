/**
 * Desktop sidebar (≥lg): frosted rail with brand, primary nav,
 * secondary destinations (plan §8.1 keeps these out of the mobile
 * bottom bar), sync status and user card. Hidden below lg — the
 * mobile bottom Navigation takes over there.
 */

import { NavLink } from 'react-router-dom';
import { ArrowRightStartOnRectangleIcon } from '@heroicons/react/24/outline';
import { PRIMARY_NAV, SECONDARY_NAV, visibleItems, type NavItem } from './nav-items';
import { useAuth, useLogout } from '../features/auth/useAuth';
import { SyncStatus } from './SyncStatus';
import { ConfirmAction } from './ConfirmAction';

function SidebarLink({ to, label, Icon }: NavItem) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        `group relative flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition-all duration-200 ${
          isActive
            ? 'bg-primary-soft text-primary font-semibold'
            : 'text-text-secondary hover:bg-surface-2/80 hover:text-text'
        }`
      }
    >
      {({ isActive }) => (
        <>
          <span
            className={`absolute left-0 top-1/2 -translate-y-1/2 h-6 w-1 rounded-r-full bg-primary transition-all duration-300 ${
              isActive ? 'opacity-100 scale-y-100' : 'opacity-0 scale-y-0'
            }`}
            aria-hidden
          />
          <Icon className={`w-5 h-5 shrink-0 ${isActive ? '' : 'opacity-80'}`} />
          <span className="flex-1">{label}</span>
        </>
      )}
    </NavLink>
  );
}

export function Sidebar() {
  const { user } = useAuth();
  const logout = useLogout();

  return (
    <aside className="hidden lg:flex fixed inset-y-0 left-0 w-64 z-40 flex-col glass border-r border-border-default px-4 py-6 safe-area-top">
      {/* Brand */}
      <div className="flex items-center gap-3 px-2 mb-8">
        <div
          className="w-10 h-10 rounded-2xl flex items-center justify-center shadow-glow shrink-0"
          style={{ background: 'linear-gradient(135deg, var(--header-from), var(--header-to))' }}
        >
          <svg viewBox="0 0 24 24" className="w-6 h-6" fill="none" aria-hidden>
            <path d="M4 9v6M7 7v10M17 7v10M20 9v6M7 12h10" stroke="var(--header-text)" strokeWidth="2.2" strokeLinecap="round" />
          </svg>
        </div>
        <div>
          <p className="font-bold text-text leading-tight">健身教练</p>
          <p className="text-xs text-text-muted">AI 私人训练</p>
        </div>
      </div>

      {/* Primary nav */}
      <nav className="space-y-1" aria-label="主导航">
        {visibleItems(PRIMARY_NAV, user?.role).map((item) => (
          <SidebarLink key={item.to} {...item} />
        ))}
      </nav>

      <div className="my-5 mx-2 h-px bg-border-default" />

      {/* Secondary destinations */}
      <nav className="space-y-1 flex-1 overflow-y-auto scrollbar-thin" aria-label="更多">
        {visibleItems(SECONDARY_NAV, user?.role).map((item) => (
          <SidebarLink key={item.to} {...item} />
        ))}
      </nav>

      {/* Sync + user */}
      <div className="pt-4 mt-2 border-t border-border-default space-y-3">
        <SyncStatus />
        <div className="flex items-center gap-3 px-2">
          <div
            className="w-9 h-9 rounded-xl flex items-center justify-center text-sm font-bold text-primary-contrast shrink-0"
            style={{ background: 'linear-gradient(135deg, var(--header-from), var(--header-to))' }}
          >
            {(user?.display_name ?? '?').slice(0, 1)}
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-sm font-medium text-text truncate">{user?.display_name}</p>
            <p className="text-xs text-text-muted">{user?.role === 'admin' ? '管理员' : '成员'}</p>
          </div>
          <ConfirmAction
            title="退出登录？"
            description="确认退出当前账号。未同步的记录仍保存在本机，重新登录后可继续同步。"
            confirmLabel="退出"
            danger
            onConfirm={async () => {
              await logout.mutateAsync();
            }}
          >
            {(trigger) => (
              <button
                onClick={trigger}
                title="退出登录"
                aria-label="退出登录"
                className="p-2 rounded-xl text-text-muted hover:text-danger hover:bg-danger-soft transition-colors"
              >
                <ArrowRightStartOnRectangleIcon className="w-5 h-5" />
              </button>
            )}
          </ConfirmAction>
        </div>
      </div>
    </aside>
  );
}
