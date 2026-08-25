"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  ApiError,
  apiFetch,
  clearToken,
  readToken,
  refreshSession,
  writeToken,
} from "@/lib/api";

export type AuthMode = "login" | "register";

export type Account = {
  id: number;
  user_code: string;
  email?: string | null;
  phone?: string | null;
  full_name?: string | null;
  status: string;
  /** Quyết định tab "Báo cáo" có hiện hay không. Backend luôn trả trường này. */
  role?: string;
};

type AuthContextValue = {
  token: string;
  account: Account | null;
  signedIn: boolean;
  isAdmin: boolean;
  ready: boolean;
  authOpen: boolean;
  authMode: AuthMode;
  openAuth: (mode?: AuthMode) => void;
  closeAuth: () => void;
  setAuthMode: (mode: AuthMode) => void;
  /** Lưu token sau khi đăng nhập/đăng ký thành công rồi nạp hồ sơ. */
  signIn: (accessToken: string, refreshToken?: string) => Promise<void>;
  signOut: () => void;
  /**
   * Gọi API kèm token hiện tại. Gặp 401 thì tự làm mới phiên rồi thử lại; chỉ
   * khi refresh token cũng hỏng mới dọn phiên và mở form đăng nhập ngay trên
   * trang đang xem — người dùng không bị đá về trang trắng.
   */
  request: <T = unknown>(
    path: string,
    init?: Omit<Parameters<typeof apiFetch>[1], "token">,
  ) => Promise<T>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth phải nằm trong <AuthProvider>");
  return value;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState("");
  const [account, setAccount] = useState<Account | null>(null);
  const [ready, setReady] = useState(false);
  const [authOpen, setAuthOpen] = useState(false);
  const [authMode, setAuthMode] = useState<AuthMode>("login");

  const signOut = useCallback(() => {
    clearToken();
    setToken("");
    setAccount(null);
  }, []);

  const openAuth = useCallback((mode: AuthMode = "login") => {
    setAuthMode(mode);
    setAuthOpen(true);
  }, []);

  const closeAuth = useCallback(() => setAuthOpen(false), []);

  const request = useCallback(
    async <T,>(
      path: string,
      init?: Omit<Parameters<typeof apiFetch>[1], "token">,
    ): Promise<T> => {
      try {
        return await apiFetch<T>(path, { ...init, token });
      } catch (error) {
        if (!(error instanceof ApiError) || !error.isUnauthorized) throw error;

        // Access token hết hạn: thử làm mới đúng một lần rồi gọi lại. Chỉ khi
        // refresh cũng hỏng mới dọn phiên và mở form đăng nhập.
        const pair = await refreshSession();
        if (!pair) {
          signOut();
          openAuth("login");
          throw error;
        }
        setToken(pair.access_token);
        return await apiFetch<T>(path, { ...init, token: pair.access_token });
      }
    },
    [token, signOut, openAuth],
  );

  const loadAccount = useCallback(async (accessToken: string) => {
    const me = await apiFetch<Account>("/auth/me", { token: accessToken });
    setAccount(me);
  }, []);

  const signIn = useCallback(
    async (accessToken: string, refreshToken?: string) => {
      writeToken(accessToken, refreshToken);
      setToken(accessToken);
      await loadAccount(accessToken);
      setAuthOpen(false);
    },
    [loadAccount],
  );

  // Khôi phục phiên khi tải lại trang. Token hỏng/hết hạn thì dọn im lặng,
  // không mở form — người dùng vẫn xem được trang chủ như khách.
  useEffect(() => {
    const saved = readToken();
    if (!saved) {
      setReady(true);
      return;
    }
    setToken(saved);
    loadAccount(saved)
      .catch(async () => {
        // Token lưu sẵn có thể đã hết hạn từ lần truy cập trước; thử làm mới
        // trước khi coi như đăng xuất.
        const pair = await refreshSession();
        if (!pair) {
          clearToken();
          return;
        }
        setToken(pair.access_token);
        await loadAccount(pair.access_token).catch(() => clearToken());
      })
      .finally(() => setReady(true));
  }, [loadAccount]);

  const value = useMemo<AuthContextValue>(
    () => ({
      token,
      account,
      signedIn: Boolean(account),
      isAdmin: account?.role === "ADMIN",
      ready,
      authOpen,
      authMode,
      openAuth,
      closeAuth,
      setAuthMode,
      signIn,
      signOut,
      request,
    }),
    [
      token,
      account,
      ready,
      authOpen,
      authMode,
      openAuth,
      closeAuth,
      signIn,
      signOut,
      request,
    ],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
