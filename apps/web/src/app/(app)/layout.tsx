import { AppSidebar } from "@/components/AppSidebar";
import { TopNav } from "@/components/TopNav";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <TopNav />
      <AppSidebar />
      <main className="pl-[220px] pt-11 min-h-screen">{children}</main>
    </>
  );
}
