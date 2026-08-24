import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { api, ApiError } from "./api";

type Role = "super_admin" | "school_admin";

interface MeShape {
  role: Role;
  school?: { id: number; slug: string; name: string; full_name: string };
  admin?: { id: number; username: string; display_name: string | null };
  super_admin_set?: boolean;
}

interface AuthCtx {
  state: "checking" | "authenticated" | "unauthenticated";
  me: MeShape | null;
  refresh: () => Promise<void>;
  logout: () => Promise<void>;
}

const Ctx = createContext<AuthCtx | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthCtx["state"]>("checking");
  const [me, setMe] = useState<MeShape | null>(null);

  const refresh = useCallback(async () => {
    try {
      const data = await api.me();
      setMe(data);
      setState("authenticated");
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) setState("unauthenticated");
      else setState("unauthenticated");
      setMe(null);
    }
  }, []);

  const logout = useCallback(async () => {
    try { await api.logout(); } catch {}
    setMe(null);
    setState("unauthenticated");
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  return <Ctx.Provider value={{ state, me, refresh, logout }}>{children}</Ctx.Provider>;
}

export function useAuth(): AuthCtx {
  const c = useContext(Ctx);
  if (!c) throw new Error("AuthProvider missing");
  return c;
}
