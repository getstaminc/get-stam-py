import React, { createContext, useContext, useState, useEffect, ReactNode, useCallback } from 'react';

const API_BASE_URL =
  process.env.REACT_APP_API_BASE_URL ||
  (process.env.NODE_ENV === "development" ? "http://127.0.0.1:5000" : "https://www.getstam.com");
const API_KEY = process.env.REACT_APP_API_KEY || "";
const TOKEN_STORAGE_KEY = "getstam_auth_token";
const DEV_PLAN_STORAGE_KEY = "getstam_dev_plan";

/** The page to come back to after Stripe Checkout/Portal, minus any earlier ?checkout= result. */
const currentReturnPath = (): string => {
  const params = new URLSearchParams(window.location.search);
  params.delete("checkout");
  const query = params.toString();
  return `${window.location.pathname}${query ? `?${query}` : ""}`;
};

export type DevPlanOverride = 'real' | 'free' | 'pro';

const readDevPlan = (): DevPlanOverride => {
  try {
    const v = localStorage.getItem(DEV_PLAN_STORAGE_KEY);
    return v === 'free' || v === 'pro' ? v : 'real';
  } catch {
    return 'real';
  }
};

export interface AuthUser {
  id: number;
  email: string;
  timezone: string;
  theme_preference: 'light' | 'dark';
  plan: 'free' | 'pro';
  subscription_status: string | null;
  trial_ends_at: string | null;
  email_verified: boolean;
}

interface AuthResult {
  success: boolean;
  error?: string;
}

interface VerifyCodeResult extends AuthResult {
  /** True when a signup-time "trial" intent produced a Checkout session and the browser is
   * already being redirected there — the caller shouldn't also navigate anywhere itself. */
  redirectingToCheckout?: boolean;
  /** Set when an access code was sent along but couldn't be redeemed — the login itself
   * still succeeded. One of the redeem-code error codes (e.g. "code_fully_redeemed"). */
  accessCodeError?: string;
}

export type SignupIntent = 'trial' | null;

interface AuthContextType {
  user: AuthUser | null;
  token: string | null;
  loading: boolean;
  isPro: boolean;
  requestCode: (email: string, intent?: SignupIntent, requireExisting?: boolean) => Promise<AuthResult>;
  verifyCode: (email: string, code: string, accessCode?: string) => Promise<VerifyCodeResult>;
  logout: () => void;
  updateProfile: (updates: { timezone?: string; theme_preference?: 'light' | 'dark' }) => Promise<AuthResult>;
  startCheckout: (startTrial?: boolean) => Promise<AuthResult>;
  openBillingPortal: () => Promise<AuthResult>;
  redeemCode: (code: string) => Promise<AuthResult>;
  /** True only when the backend runs with FLASK_ENV=development (see /api/dev/config). */
  devTools: boolean;
  devPlan: DevPlanOverride;
  setDevPlan: (plan: DevPlanOverride) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

async function parseError(res: Response, fallback: string): Promise<string> {
  try {
    const data = await res.json();
    return data.error || fallback;
  } catch {
    return fallback;
  }
}

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(TOKEN_STORAGE_KEY));
  const [loading, setLoading] = useState<boolean>(true);

  const clearAuth = useCallback(() => {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    setToken(null);
    setUser(null);
  }, []);

  useEffect(() => {
    if (!token) {
      setLoading(false);
      return;
    }
    let cancelled = false;
    fetch(`${API_BASE_URL}/api/auth/me`, {
      headers: { "X-API-KEY": API_KEY, "Authorization": `Bearer ${token}` },
    })
      .then(async (res) => {
        if (res.status === 401 || res.status === 403) {
          // Token is genuinely bad — drop it.
          if (!cancelled) clearAuth();
          return;
        }
        if (!res.ok) {
          // Transient (5xx / network). Keep the token so a refresh recovers instead of
          // silently logging the user out — e.g. right after returning from Stripe Checkout.
          return;
        }
        const data = await res.json();
        if (!cancelled) setUser(data.user);
      })
      .catch(() => {
        // Network failure — keep the token, let a later load retry.
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  const requestCode = useCallback(async (email: string, intent: SignupIntent = null, requireExisting: boolean = false): Promise<AuthResult> => {
    const res = await fetch(`${API_BASE_URL}/api/auth/request-code`, {
      method: "POST",
      headers: { "X-API-KEY": API_KEY, "Content-Type": "application/json" },
      body: JSON.stringify({ email, intent, require_existing: requireExisting }),
    });
    if (!res.ok) {
      // The per-IP limiter (5/hour on this route) answers 429 without our JSON error body.
      const fallback = res.status === 429
        ? "Too many code requests — please try again in an hour."
        : "Could not send login code";
      return { success: false, error: await parseError(res, fallback) };
    }
    return { success: true };
  }, []);

  const verifyCode = useCallback(async (email: string, code: string, accessCode?: string): Promise<VerifyCodeResult> => {
    const res = await fetch(`${API_BASE_URL}/api/auth/verify-code`, {
      method: "POST",
      headers: { "X-API-KEY": API_KEY, "Content-Type": "application/json" },
      body: JSON.stringify({ email, code, access_code: accessCode || undefined, return_path: currentReturnPath() }),
    });
    if (!res.ok) return { success: false, error: await parseError(res, "That code is invalid or has expired") };
    const data = await res.json();
    localStorage.setItem(TOKEN_STORAGE_KEY, data.token);
    setToken(data.token);
    setUser(data.user);
    if (data.checkout_url) {
      window.location.href = data.checkout_url;
      return { success: true, redirectingToCheckout: true };
    }
    return { success: true, accessCodeError: data.access_code_error };
  }, []);

  const logout = useCallback(() => {
    clearAuth();
  }, [clearAuth]);

  const updateProfile = useCallback(async (updates: { timezone?: string; theme_preference?: 'light' | 'dark' }): Promise<AuthResult> => {
    if (!token) return { success: false, error: "not_logged_in" };
    const res = await fetch(`${API_BASE_URL}/api/auth/me`, {
      method: "PATCH",
      headers: { "X-API-KEY": API_KEY, "Authorization": `Bearer ${token}`, "Content-Type": "application/json" },
      body: JSON.stringify(updates),
    });
    if (!res.ok) return { success: false, error: await parseError(res, "Could not update profile") };
    const data = await res.json();
    setUser(data.user);
    return { success: true };
  }, [token]);

  const startCheckout = useCallback(async (startTrial: boolean = true): Promise<AuthResult> => {
    if (!token) return { success: false, error: "not_logged_in" };
    const res = await fetch(`${API_BASE_URL}/api/billing/checkout-session`, {
      method: "POST",
      headers: { "X-API-KEY": API_KEY, "Authorization": `Bearer ${token}`, "Content-Type": "application/json" },
      body: JSON.stringify({ trial: startTrial, return_path: currentReturnPath() }),
    });
    if (!res.ok) return { success: false, error: await parseError(res, "Could not start checkout") };
    const data = await res.json();
    window.location.href = data.url;
    return { success: true };
  }, [token]);

  const redeemCode = useCallback(async (code: string): Promise<AuthResult> => {
    if (!token) return { success: false, error: "not_logged_in" };
    const res = await fetch(`${API_BASE_URL}/api/billing/redeem-code`, {
      method: "POST",
      headers: { "X-API-KEY": API_KEY, "Authorization": `Bearer ${token}`, "Content-Type": "application/json" },
      body: JSON.stringify({ code }),
    });
    if (!res.ok) return { success: false, error: await parseError(res, "Could not redeem code") };
    const data = await res.json();
    setUser(data.user);
    return { success: true };
  }, [token]);

  const openBillingPortal = useCallback(async (): Promise<AuthResult> => {
    if (!token) return { success: false, error: "not_logged_in" };
    const res = await fetch(`${API_BASE_URL}/api/billing/portal-session`, {
      method: "POST",
      headers: { "X-API-KEY": API_KEY, "Authorization": `Bearer ${token}`, "Content-Type": "application/json" },
      body: JSON.stringify({ return_path: currentReturnPath() }),
    });
    if (!res.ok) return { success: false, error: await parseError(res, "Could not open billing portal") };
    const data = await res.json();
    window.location.href = data.url;
    return { success: true };
  }, [token]);

  // Dev-only plan override: lets you preview the free vs Pro UI on any page.
  // Frontend-only — backend gates (e.g. MLB trend length) still use the real plan.
  const [devTools, setDevTools] = useState(false);
  const [devPlan, setDevPlanState] = useState<DevPlanOverride>(readDevPlan);

  useEffect(() => {
    fetch(`${API_BASE_URL}/api/dev/config`)
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => setDevTools(!!data?.dev_tools))
      .catch(() => {});
  }, []);

  const setDevPlan = useCallback((plan: DevPlanOverride) => {
    try { localStorage.setItem(DEV_PLAN_STORAGE_KEY, plan); } catch {}
    setDevPlanState(plan);
  }, []);

  const realIsPro = user?.plan === 'pro';
  const isPro = devTools && devPlan !== 'real' ? devPlan === 'pro' : realIsPro;

  return (
    <AuthContext.Provider value={{ user, token, loading, isPro, requestCode, verifyCode, logout, updateProfile, startCheckout, openBillingPortal, redeemCode, devTools, devPlan, setDevPlan }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
