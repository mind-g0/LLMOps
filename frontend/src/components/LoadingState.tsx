import type { ReactNode } from "react";

export function LoadingState({ label = "Loading" }: { label?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-16 text-ink-500" role="status">
      <span className="h-6 w-6 animate-spin rounded-full border-2 border-ink-200 border-t-signal" />
      <p className="text-sm">{label}&hellip;</p>
    </div>
  );
}

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-ink-200 px-6 py-16 text-center">
      <p className="text-sm font-medium text-ink-800">{title}</p>
      {description && <p className="max-w-sm text-sm text-ink-500">{description}</p>}
      {action && <div className="mt-3">{action}</div>}
    </div>
  );
}

export function ErrorState({
  title = "Something went wrong",
  description,
  onRetry,
}: {
  title?: string;
  description?: string;
  onRetry?: () => void;
}) {
  return (
    <div
      className="flex flex-col items-center justify-center gap-2 rounded-lg border border-rejected-border bg-rejected-bg px-6 py-16 text-center"
      role="alert"
    >
      <p className="text-sm font-medium text-rejected">{title}</p>
      {description && <p className="max-w-sm text-sm text-ink-600">{description}</p>}
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="focus-ring mt-3 rounded-md border border-rejected-border bg-white px-3 py-1.5 text-sm font-medium text-rejected hover:bg-rejected-bg"
        >
          Try again
        </button>
      )}
    </div>
  );
}
