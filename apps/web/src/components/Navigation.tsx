/**
 * Navigation (plan §8.1): mobile bottom bar fixed to
 * 今日 / 记录 / 教练 / 我的; knowledge/reviews/nutrition/settings live
 * behind page entries, not the bottom bar.
 */

import { NavLink } from 'react-router-dom';
import {
  HomeIcon,
  ClipboardDocumentListIcon,
  ChatBubbleLeftRightIcon,
  UserCircleIcon,
} from '@heroicons/react/24/outline';
import {
  HomeIcon as HomeIconSolid,
  ClipboardDocumentListIcon as ClipboardIconSolid,
  ChatBubbleLeftRightIcon as ChatIconSolid,
  UserCircleIcon as UserCircleIconSolid,
} from '@heroicons/react/24/solid';

const NAV_ITEMS = [
  { to: '/today', label: '今日', Icon: HomeIcon, IconActive: HomeIconSolid },
  { to: '/history', label: '记录', Icon: ClipboardDocumentListIcon, IconActive: ClipboardIconSolid },
  { to: '/chat', label: '教练', Icon: ChatBubbleLeftRightIcon, IconActive: ChatIconSolid },
  { to: '/settings', label: '我的', Icon: UserCircleIcon, IconActive: UserCircleIconSolid },
];

export function Navigation() {
  return (
    <nav className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 safe-area-bottom z-50">
      <div className="flex justify-around max-w-md mx-auto">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              `flex flex-col items-center py-3 px-4 flex-1 transition-colors ${
                isActive ? 'text-primary-600' : 'text-gray-600'
              }`
            }
          >
            {({ isActive }) => (
              <>
                {isActive ? <item.IconActive className="w-6 h-6" /> : <item.Icon className="w-6 h-6" />}
                <span className="text-xs mt-1 font-medium">{item.label}</span>
              </>
            )}
          </NavLink>
        ))}
      </div>
    </nav>
  );
}
