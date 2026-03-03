import { getServerSession } from "next-auth/next";
import { redirect } from "next/navigation";
import { authOptions } from "@/lib/auth";
import { Sidebar } from "@/components/sidebar";
import { FeedbackWidget } from "@/components/feedback/feedback-widget";
import { OnboardingGuide } from "@/components/onboarding/onboarding-guide";

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
      <div className="flex-1 md:ml-60">
        <main className="px-4 sm:px-8 py-8 pt-16 md:pt-8">
          <OnboardingGuide />
          {children}
        </main>
      </div>
      <FeedbackWidget />
    </div>
  );
}
