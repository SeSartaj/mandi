import { toast, type ExternalToast } from "sonner";

/**
 * Thin wrapper around Sonner so features do not import the library directly.
 * Messages are translated by the caller; descriptions can carry the API error.
 */
export const notify = {
  success: (message: string, options?: ExternalToast) => toast.success(message, options),
  error: (message: string, options?: ExternalToast) => toast.error(message, options),
  info: (message: string, options?: ExternalToast) => toast.info(message, options),
  loading: (message: string, options?: ExternalToast) => toast.loading(message, options),
  dismiss: (id?: string | number) => toast.dismiss(id),
};
