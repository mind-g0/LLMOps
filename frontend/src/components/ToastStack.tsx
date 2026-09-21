import type { ToastMessage } from "@/hooks/useToast";

export function ToastStack({
  toasts,
  onDismiss,
}: {
  toasts: ToastMessage[];
  onDismiss: (id: number) => void;
}) {
  if (toasts.length === 0) return null;

  return (
    <div className="pointer-events-none fixed bottom-4 right-4 z-50 flex flex-col gap-2">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          role="status"
          className={`pointer-events-auto flex items-center gap-3 rounded-md border px-4 py-2.5 text-sm shadow-panel ${
            toast.tone === "success"
              ? "border-approved-border bg-white text-approved"
              : "border-rejected-border bg-white text-rejected"
          }`}
        >
          {toast.text}
          <button
            type="button"
            onClick={() => onDismiss(toast.id)}
            aria-label="Dismiss notification"
            className="focus-ring rounded text-ink-400 hover:text-ink-700"
          >
            &times;
          </button>
        </div>
      ))}
    </div>
  );
}
