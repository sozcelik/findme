"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Folder,
  FileText,
  Zap,
  BarChart2,
  Settings,
  Search,
  type LucideIcon,
} from "lucide-react";

interface NavItem {
  key: string;
  label: string;
  href: string;
  Icon: LucideIcon;
}

const NAV_ITEMS: NavItem[] = [
  { key: "dashboard", label: "Dashboard", href: "/dashboard", Icon: LayoutDashboard },
  { key: "projects", label: "Projects", href: "/projects", Icon: Folder },
  { key: "content", label: "Content", href: "/content", Icon: FileText },
  { key: "campaigns", label: "Campaigns", href: "/campaigns", Icon: Zap },
  { key: "visibility", label: "Visibility", href: "/visibility", Icon: BarChart2 },
];

export function AppSidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed top-11 left-0 bottom-0 w-[220px] bg-sidebar flex flex-col z-40 border-r border-sidebar-border">
      {/* Search */}
      <div className="px-2 pt-2.5 pb-1.5">
        <div className="flex items-center gap-2 px-2.5 h-7 rounded-md bg-muted/70 border border-border text-muted-foreground cursor-pointer hover:bg-muted transition-colors">
          <Search size={12} strokeWidth={2} />
          <span className="text-[12px] flex-1 select-none">Search</span>
          <span className="text-[10px] font-mono bg-background border border-border rounded px-1 py-px leading-none select-none">
            ⌘K
          </span>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto px-2 py-1 no-scrollbar">
        <div className="space-y-0.5">
          {NAV_ITEMS.map(({ key, label, href, Icon }) => {
            const isActive = pathname === href || pathname.startsWith(href + "/");
            return (
              <Link
                key={key}
                href={href}
                className={[
                  "flex items-center gap-2.5 px-3 py-1.5 rounded-md text-[12.5px] transition-colors",
                  isActive
                    ? "bg-sidebar-accent text-sidebar-foreground font-medium"
                    : "text-muted-foreground hover:text-sidebar-foreground hover:bg-sidebar-accent",
                ].join(" ")}
              >
                <Icon
                  size={13.5}
                  strokeWidth={isActive ? 2.5 : 2}
                  className={isActive ? "text-primary" : "text-muted-foreground"}
                />
                {label}
              </Link>
            );
          })}
        </div>
      </nav>

      {/* Footer */}
      <div className="px-2 py-2 border-t border-sidebar-border">
        <Link
          href="/settings"
          className={[
            "flex items-center gap-2.5 px-3 py-1.5 rounded-md text-[12.5px] transition-colors",
            pathname.startsWith("/settings")
              ? "bg-sidebar-accent text-sidebar-foreground font-medium"
              : "text-muted-foreground hover:text-sidebar-foreground hover:bg-sidebar-accent",
          ].join(" ")}
        >
          <Settings
            size={13.5}
            strokeWidth={pathname.startsWith("/settings") ? 2.5 : 2}
            className={pathname.startsWith("/settings") ? "text-primary" : "text-muted-foreground"}
          />
          Settings
        </Link>
      </div>
    </aside>
  );
}
