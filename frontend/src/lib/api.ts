const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api";

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
  ) {
    super(message);
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;

  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });

  if (!res.ok) {
    let code = "unknown_error";
    let message = `Request failed with status ${res.status}`;
    try {
      const body = await res.json();
      code = body.code ?? code;
      message = body.message ?? message;
    } catch {
      // response had no JSON body
    }
    throw new ApiError(res.status, code, message);
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

// ---- Types mirroring backend Pydantic schemas ----
export type UserRole = "student" | "instructor" | "admin" | "super_admin";

export interface UserOut {
  id: number;
  name: string;
  email: string;
  role: UserRole;
  is_active: boolean;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface FeatureContribution {
  feature: string;
  contribution: number;
  direction: "positive" | "negative";
}

export interface PredictionResponse {
  student_id: number;
  generated_at: string;
  classification: {
    predicted_category: string;
    risk_level: "LOW" | "MEDIUM" | "HIGH";
    confidence: number;
    model_version: string;
    explanation: FeatureContribution[];
  };
  regression: {
    predicted_gpa: number;
    model_version: string;
    explanation: FeatureContribution[];
  };
  disclaimer: string;
}

// ---- API functions ----
export const api = {
  login: (email: string, password: string) =>
    request<TokenResponse>("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),

  register: (name: string, email: string, password: string, role: UserRole) =>
    request<UserOut>("/auth/register", { method: "POST", body: JSON.stringify({ name, email, password, role }) }),

  me: () => request<UserOut>("/auth/me"),

  generatePrediction: (studentId: number) =>
    request<PredictionResponse>(`/predictions/students/${studentId}`, { method: "POST" }),
};

export function saveTokens(tokens: TokenResponse) {
  localStorage.setItem("access_token", tokens.access_token);
  localStorage.setItem("refresh_token", tokens.refresh_token);
}

export function clearTokens() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
}
