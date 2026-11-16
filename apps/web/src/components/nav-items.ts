/**
 * Shared navigation model (plan §8.1).
 *
 * Primary items mirror the mobile bottom bar (今日/记录/教练/我的);
 * secondary items live behind page entries on mobile and become direct
 * links in the desktop sidebar. `adminOnly` items are filtered by role.
 */

import {
  HomeIcon,
  ClipboardDocumentListIcon,
  ChatBubbleLeftRightIcon,
  UserCircleIcon,
  CalendarDaysIcon,
  BookOpenIcon,
  ChartBarIcon,
  CakeIcon,
  WrenchScrewdriverIcon,
} from '@heroicons/react/24/outline';
import type { ComponentType, SVGProps } from 'react';

export interface NavItem {
  to: string;
  label: string;
  Icon: ComponentType<SVGProps<SVGSVGElement>>;
  adminOnly?: boolean;
}

export const PRIMARY_NAV: NavItem[] = [
  { to: '/today', label: '今日', Icon: HomeIcon },
  { to: '/history', label: '记录', Icon: ClipboardDocumentListIcon },
  { to: '/chat', label: '教练', Icon: ChatBubbleLeftRightIcon },
  { to: '/settings', label: '我的', Icon: UserCircleIcon },
];

export const SECONDARY_NAV: NavItem[] = [
  { to: '/plans', label: '计划', Icon: CalendarDaysIcon },
  { to: '/knowledge', label: '知识库', Icon: BookOpenIcon },
  { to: '/reviews', label: '周复盘', Icon: ChartBarIcon },
  { to: '/nutrition', label: '饮食', Icon: CakeIcon },
  { to: '/admin/catalog', label: '内容管理', Icon: WrenchScrewdriverIcon, adminOnly: true },
];

/** Filter items by the user's role. */
export function visibleItems(items: NavItem[], role: string | undefined): NavItem[] {
  return items.filter((item) => !item.adminOnly || role === 'admin');
}
