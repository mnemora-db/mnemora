"use client";

import { toast } from "sonner";

export function NotifyButton({ connectorName }: { connectorName: string }) {
  return (
    <button
      onClick={() =>
        toast.success(
          `We'll notify you when ${connectorName} is ready!`
        )
      }
      className="inline-flex items-center justify-center rounded-md border border-[#3F3F46] bg-[#18181B] px-4 py-2 text-sm font-medium text-[#A1A1AA] hover:text-[#FAFAFA] hover:border-[#52525B] transition-colors duration-150"
    >
      Notify Me
    </button>
  );
}
