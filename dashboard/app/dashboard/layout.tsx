import { Sidebar } from "@/components/sidebar";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen bg-[#09090B]">
      <Sidebar />
      <div className="flex-1 ml-60">
        <main className="px-8 py-8">{children}</main>
      </div>
    </div>
  );
}
