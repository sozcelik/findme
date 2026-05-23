import Link from "next/link";

const tabs = [
  { label: "Integrations", href: "/settings/integrations" },
  { label: "Billing", href: "/settings/billing" },
];

export default function SettingsLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="p-8 max-w-4xl">
      <h1 className="text-2xl font-semibold mb-6">Settings</h1>
      <div className="flex gap-1 mb-8 border-b border-border">
        {tabs.map((t) => (
          <Link
            key={t.href}
            href={t.href}
            className="px-4 py-2 text-sm font-medium text-muted-foreground hover:text-foreground border-b-2 border-transparent hover:border-primary transition-colors"
          >
            {t.label}
          </Link>
        ))}
      </div>
      {children}
    </div>
  );
}
