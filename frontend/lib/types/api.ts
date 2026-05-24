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

export type DocumentStatus =
  | 'PENDING'
  | 'PARSING'
  | 'CHUNKING'
  | 'EMBEDDING'
  | 'READY'
  | 'FAILED';

export interface DocumentSummary {
  document_id: string;
  name: string;
  size_bytes: number;
  uploaded_at: string;
  status: DocumentStatus;
  required_level: number;
  allowed_groups: string[];
}

export interface DocumentRead extends DocumentSummary {
  original_filename: string;
  mime_type: string;
  chunk_count: number;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentListResponse {
  items: DocumentSummary[];
  total: number;
}

export interface UploadDocumentResponse {
  document_id: string;
  status: DocumentStatus;
}

export interface UpdateDocumentAclRequest {
  required_level: number;
  allowed_groups: string[];
}

export interface ReindexDocumentResponse {
  document_id: string;
  status: DocumentStatus;
}

export const PROCESSING_DOCUMENT_STATUSES: readonly DocumentStatus[] = [
  'PENDING',
  'PARSING',
  'CHUNKING',
  'EMBEDDING',
] as const;

export function normalizeDocumentStatus(status: string): DocumentStatus {
  return status.toUpperCase() as DocumentStatus;
}

export function isProcessingDocumentStatus(status: DocumentStatus): boolean {
  return (PROCESSING_DOCUMENT_STATUSES as readonly string[]).includes(status);
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

// ── Chat (Phase 3) ──────────────────────────────────────────────────────────

export interface Citation {
  citation_id: number;
  document_id: string;
  doc_name: string;
  page?: number | null;
}

export interface ChatSessionRead {
  session_id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface ChatSessionListItem {
  session_id: string;
  title: string;
  updated_at: string;
  message_count: number;
}

export interface ChatSessionListResponse {
  items: ChatSessionListItem[];
  total: number;
}

export interface ChatMessageRead {
  message_id: string;
  role: 'user' | 'assistant';
  content: string;
  citations?: Citation[] | null;
  error_code?: string | null;
  created_at: string;
}

export interface ChatMessageListResponse {
  items: ChatMessageRead[];
}

export interface ChatStreamRequest {
  session_id?: string;
  query: string;
  include_debug?: boolean;
}

export interface ChunkTraceChunk {
  chunk_id: string;
  document_id: string;
  document_name: string;
  text: string;
  page_number?: number | null;
  section_path?: string[];
  heading_context?: string;
  vector_score?: number;
  rerank_score?: number | null;
  citation_id?: number;
}

export interface ChunkTraceRead {
  trace_id: string;
  message_id: string;
  query: string;
  embedding_model: string;
  llm_model: string;
  retrieved_chunks: ChunkTraceChunk[];
  used_chunks: ChunkTraceChunk[];
  final_prompt?: string | null;
  latency_ms: number;
  latency_breakdown?: Record<string, number> | null;
  token_usage?: Record<string, number> | null;
  created_at: string;
}

export type ChatStreamEventType =
  | 'start'
  | 'token'
  | 'tool_call'
  | 'tool_result'
  | 'citations'
  | 'done'
  | 'error';

export interface ChatStreamEvent {
  type: ChatStreamEventType;
  data: unknown;
}
