// Mirror types từ backend Pydantic schemas. Manual sync (Phase 1).
// Sau Phase 3 sẽ generate từ OpenAPI spec.

export type UserRole = 'admin' | 'user';
export type UserStatus = 'pending_approval' | 'active' | 'locked' | 'disabled';

export interface Group {
  id: string;
  name: string;
  description: string | null;
}

export interface UserSummary {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
}

export interface UserRead {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  access_level: number;
  status: UserStatus;
  groups: Group[];
  last_login_at: string | null;
  created_at: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: 'bearer';
  expires_in: number;
  user: UserSummary;
}

export interface RegisterRequest {
  email: string;
  password: string;
  full_name: string;
}

export interface RegisterResponse {
  user_id: string;
  status: UserStatus;
  message: string;
}

export interface RefreshResponse {
  access_token: string;
  token_type: 'bearer';
  expires_in: number;
}

export interface MessageResponse {
  message: string;
}

export interface ApiErrorPayload {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

export interface ApiErrorResponse {
  error: ApiErrorPayload;
}

export class ApiError extends Error {
  code: string;
  status: number;
  details: Record<string, unknown>;

  constructor(payload: ApiErrorPayload, status: number) {
    super(payload.message);
    this.code = payload.code;
    this.status = status;
    this.details = payload.details ?? {};
    this.name = 'ApiError';
  }
}
