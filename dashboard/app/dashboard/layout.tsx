import { getServerSession } from "next-auth/next";
import { redirect } from "next/navigation";
import { authOptions } from "@/lib/auth";
import { Sidebar } from "@/components/sidebar";

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const session = await getServerSession(authOptions);

  if (!session) {
    redirect("/");
  }

  return (
    <div className="flex min-h-screen bg-[#09090B]">
      <Sidebar />
      <div className="flex-1 ml-60">
        <main className="px-8 py-8">{children}</main>
      </div>
    </div>
  );
}
