import { Link } from "react-router-dom";

export function NotFoundPage() {
  return (
    <div className="bg-background text-on-background min-h-screen flex items-center justify-center font-body-md relative overflow-hidden">
      <div className="absolute inset-0 z-0">
        <div className="absolute inset-0 bg-surface" />
        <div className="absolute inset-0 cyber-grid" />
      </div>
      <div className="z-10 text-center">
        <div className="font-display-lg text-display-lg text-primary">404</div>
        <p className="text-on-surface-variant mb-6 mt-2">That page doesn't exist.</p>
        <Link
          to="/"
          className="inline-flex items-center gap-2 bg-primary text-on-primary px-5 py-2.5 rounded-md font-bold text-sm hover:bg-primary/90 transition-colors shadow-[0_0_10px_rgba(200,198,197,0.3)]"
        >
          <span className="material-symbols-outlined text-[18px]">home</span>
          Back to dashboard
        </Link>
      </div>
    </div>
  );
}
