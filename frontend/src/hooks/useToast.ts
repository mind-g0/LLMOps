import { useCallback, useState } from "react";

export interface ToastMessage {
  id: number;
  tone: "success" | "error";
  text: string;
}

let nextId = 1;

export function useToast() {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const showToast = useCallback((text: string, tone: ToastMessage["tone"] = "success") => {
    const id = nextId++;
    setToasts((current) => [...current, { id, tone, text }]);
    setTimeout(() => {
      setToasts((current) => current.filter((t) => t.id !== id));
    }, 4000);
  }, []);

  const dismissToast = useCallback((id: number) => {
    setToasts((current) => current.filter((t) => t.id !== id));
  }, []);

  return { toasts, showToast, dismissToast };
}
