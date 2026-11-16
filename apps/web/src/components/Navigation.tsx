/**
 * Mobile bottom navigation (plan §8.1, < lg only — the desktop Sidebar
 * takes over at ≥1024px): 今日 / 记录 / 教练 / 我的. Frosted glass +
 * animated active indicator + iOS safe-area padding.
 */

import { NavLink } from 'react-router-dom';
import { PRIMARY_NAV, visibleItems } from './nav-items';
import { useAuth } from '../features/auth/useAuth';
import {
  HomeIcon as HomeSolid,
  ClipboardDocumentListIcon as ClipboardSolid,
  ChatBubbleLeftRightIcon as ChatSolid,
  UserCircleIcon as UserSolid,
} from '@heroicons/react/24/solid';

const SOLID_ICONS: Record<string, typeof HomeSolid> = {
  '/today': HomeSolid,
  '/history': ClipboardSolid,
  '/chat': ChatSolid,
  '/settings': UserSolid,
};

export function Navigation() {
  const { user } = useAuth();
  const items = visibleItems(PRIMARY_NAV, user?.role);

  return (
    <nav className="fixed bottom-0 left-0 right-0 glass border-t border-border-default safe-area-bottom z-50">
      <div className="flex justify-around max-w-md mx-auto">
        {items.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              `relative flex flex-col items-center py-2.5 px-4 flex-1 transition-colors duration-200 ${
                isActive ? 'text-primary' : 'text-text-muted hover:text-text-secondary'
              }`
            }
          >
            {({ isActive }) => {
              const IconActive = SOLID_ICONS[item.to];
              return (
                <>
                  {/* animated active pill */}
                  <span
                    className={`absolute top-0 left-1/2 -translate-x-1/2 h-1 rounded-b-full bg-primary transition-all duration-300 ${
                      isActive ? 'w-8 opacity-100' : 'w-0 opacity-0'
                    }`}
                    aria-hidden
                  />
                  <span
                    className={`transition-transform duration-200 ${isActive ? 'scale-110 -translate-y-0.5' : ''}`}
                  >
                    {isActive && IconActive ? (
                      <IconActive className="w-6 h-6" />
                    ) : (
                      <item.Icon className="w-6 h-6" />
                    )}
                  </span>
                  <span className={`text-xs mt-1 ${isActive ? 'font-semibold' : 'font-medium'}`}>{item.label}</span>
                </>
              );
            }}
          </NavLink>
        ))}
      </div>
    </nav>
  );
}
