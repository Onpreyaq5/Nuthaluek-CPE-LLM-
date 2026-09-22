import { createContext, useContext, useState, type ReactNode } from "react";
import type { CurrentUser, Section } from "@/api/types";
type AppState = {
  user: CurrentUser | null;
  setUser: (u: CurrentUser | null) => void;
  draft: Section[];
  setDraft: (s: Section[]) => void;
  notify: (text: string) => void;
  toast: string;
};
const Context = createContext<AppState | null>(null);
export function StateProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<CurrentUser | null>(null),
    [draft, setDraft] = useState<Section[]>([]),
    [toast, setToast] = useState("");
  function notify(text: string) {
    setToast(text);
    window.setTimeout(
      () => setToast((current) => (current === text ? "" : current)),
      4200,
    );
  }
  return (
    <Context.Provider value={{ user, setUser, draft, setDraft, notify, toast }}>
      {children}
    </Context.Provider>
  );
}
export function useApp() {
  const value = useContext(Context);
  if (!value) throw new Error("Missing app context");
  return value;
}
