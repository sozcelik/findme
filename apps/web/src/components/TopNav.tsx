import Link from "next/link";

export function TopNav() {
  return (
    <header className="fixed top-0 left-0 right-0 h-11 z-50 bg-background/95 backdrop-blur border-b border-border flex items-center px-4 gap-4">
      <Link
        href="/dashboard"
        className="text-[13px] font-bold font-display text-foreground tracking-tight select-none"
      >
        findme
      </Link>
      <div className="flex-1" />
      <Link
        href="/settings"
        className="text-xs text-muted-foreground hover:text-foreground transition-colors"
      >
        Settings
      </Link>
    </header>
  );
}
