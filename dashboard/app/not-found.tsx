import Link from "next/link";

export default function NotFound() {
  return (
    <div className="min-h-screen bg-[#09090B] flex items-center justify-center px-4">
      <div className="text-center max-w-md">
        <p className="text-7xl font-bold text-[#27272A] select-none">404</p>
        <h1 className="mt-4 text-xl font-semibold text-[#FAFAFA] tracking-tight">
          Page not found
        </h1>
        <p className="mt-2 text-sm text-[#71717A]">
          The page you&apos;re looking for doesn&apos;t exist or has been moved.
        </p>
        <Link
          href="/"
          className="mt-6 inline-flex items-center gap-1.5 px-4 py-2 rounded-md bg-[#2DD4BF] text-[#09090B] text-sm font-semibold hover:bg-[#2DD4BF]/90 transition-colors duration-150"
        >
          Go home
        </Link>
      </div>
    </div>
  );
}
