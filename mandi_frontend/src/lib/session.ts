import { createContext, useContext } from "react";
import type { Session } from "./api";
export const SessionContext = createContext<(Session & { signout: () => Promise<void> }) | null>(
  null,
);
export const useSession = () => useContext(SessionContext)!;
