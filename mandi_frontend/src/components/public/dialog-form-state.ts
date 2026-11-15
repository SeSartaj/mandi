import { createContext } from "react";

export const DialogFormState = createContext<
  ((state: { dirty: boolean; busy: boolean }) => void) | null
>(null);
