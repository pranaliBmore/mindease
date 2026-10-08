/**
 * Dev: same-origin + Vite proxy to backend.
 * Prod: same-origin `/api` when the API is reverse-proxied with the SPA; otherwise set VITE_API_BASE_URL.
 */
const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL !== undefined && import.meta.env.VITE_API_BASE_URL !== ""
    ? import.meta.env.VITE_API_BASE_URL
    : "";

type HttpMethod = "GET" | "POST" | "PATCH";

function authHeaders(): Record<string, string> {
  const token = localStorage.getItem("accessToken");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function decodeJwtExpiry(token: string): number | null {
  try {
    const base64 = token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
    const json = JSON.parse(atob(base64)) as { exp?: number };
    return typeof json.exp === "number" ? json.exp * 1000 : null;
  } catch {
    return null;
  }
}

/** True only for a present, well-formed, non-expired access token - checked
 * synchronously so route guards can decide before ever rendering protected content. */
export function hasValidSession(): boolean {
  const token = localStorage.getItem("accessToken");
  if (!token) return false;
  const expiresAt = decodeJwtExpiry(token);
  return expiresAt !== null && expiresAt > Date.now();
}

export function clearSession(): void {
  localStorage.removeItem("accessToken");
  localStorage.removeItem("refreshToken");
}

/** Resolves a backend-relative media path (e.g. an avatar_url) against the API origin. */
export function resolveMediaUrl(path: string | null | undefined): string | null {
  if (!path) return null;
  if (/^https?:\/\//.test(path)) return path;
  return `${API_BASE_URL}${path}`;
}

/** FastAPI returns detail as string, object, or validation array */
function formatErrorDetail(data: { detail?: unknown }): string {
  const detail = data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const parts = detail.map((item: { msg?: string; loc?: unknown[] }) => {
      if (typeof item?.msg === "string") return item.msg;
      return JSON.stringify(item);
    });
    return parts.length ? parts.join(" ") : "Validation error";
  }
  if (detail && typeof detail === "object" && "message" in detail) {
    return String((detail as { message: string }).message);
  }
  return "Request failed";
}

async function request<T>(
  path: string,
  method: HttpMethod,
  body?: unknown,
  isFormData = false,
): Promise<T> {
  const headers: Record<string, string> = { ...authHeaders() };
  if (method !== "GET" && !isFormData) {
    headers["Content-Type"] = "application/json";
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers,
      body:
        method === "GET"
          ? undefined
          : body
            ? isFormData
              ? (body as FormData)
              : JSON.stringify(body)
            : undefined,
    });
  } catch {
    throw new Error(
      "Cannot reach API. Start the backend (backend/./run_backend.sh) and ensure port 8000 is free.",
    );
  }

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    if (response.status === 401 && path !== "/api/auth/login" && path !== "/api/auth/signup") {
      clearSession();
      if (typeof window !== "undefined" && window.location.pathname !== "/") {
        window.location.assign("/");
      }
    }
    throw new Error(formatErrorDetail(data));
  }
  return data as T;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  email_verified: boolean;
}

export interface EmotionResponse {
  id: string;
  emotion: string;
  confidence: number;
  description: string;
}

export interface PublicUser {
  id: string;
  name: string;
  email_masked: string;
  avatar_url: string | null;
  bio: string;
}

export interface DiscoverUser extends PublicUser {
  mood: string | null;
  shares_your_mood: boolean;
}

export interface UserMe {
  id: string;
  name: string;
  email: string;
  avatar_url: string | null;
  bio: string;
  email_verified: boolean;
  emotional_history: string[];
  feedback_history: string[];
  communities: string[];
  connections: string[];
  created_at: string;
}

export interface ConnectionRequestItem {
  request_id: string;
  user: PublicUser;
  created_at: string | null;
}

export interface AcceptedConnectionItem {
  request_id: string;
  user: PublicUser;
  accepted_at: string | null;
}

export interface ConnectionStateResponse {
  incoming_pending: ConnectionRequestItem[];
  outgoing_pending: ConnectionRequestItem[];
  connections: AcceptedConnectionItem[];
}

export interface DirectMessageItem {
  id: string;
  from_user_id: string;
  to_user_id: string;
  body: string;
  created_at: string | null;
}

export type SoloEmotion = "stress" | "anxiety" | "sadness" | "happiness" | "anger" | "fear" | "neutrality";

export interface SoloSuggestionPack {
  exercises: string[];
  quotes: string[];
  videos: { title: string; url: string }[];
  tips: string[];
}

export interface SoloAnalyzeResponse {
  session_id: string;
  emotion: SoloEmotion;
  confidence: number;
  model_used: string;
  suggestions: SoloSuggestionPack;
}

export interface ChatResponse {
  reply: string;
  provider_used: string;
  intent?: string;
  detected_emotion?: string;
  safety?: string;
}

export type ChatMode = "chat" | "breathing" | "grounding" | "journal_prompt" | "reframe" | "pep_talk";

export interface ChatHistoryItem {
  id: string;
  user_message: string;
  ai_reply: string;
  provider_used: string;
  created_at: string;
}

export interface ChatHistoryResponse {
  messages: ChatHistoryItem[];
}

export type CommunityMood = SoloEmotion;

export interface PostAuthor {
  id: string;
  name: string;
  avatar_url: string | null;
}

export interface CommunityComment {
  id: string;
  user_id: string;
  name: string;
  avatar_url: string | null;
  text: string;
  created_at: string | null;
}

export interface CommunityPost {
  id: string;
  author: PostAuthor;
  text: string;
  mood: CommunityMood;
  created_at: string;
  likes: number;
  liked_by_me: boolean;
  comments: CommunityComment[];
}

export interface CommunityFeedResponse {
  items: CommunityPost[];
}

export interface CommunityDetails {
  name: string;
  member_count: number;
  recent_posts: CommunityPost[];
}

export interface FeedbackResponse {
  id: string;
  flow_type: string;
  content_type: string | null;
  message: string;
  rating: number;
  created_at: string;
}

export interface GenericMessageResponse {
  message: string;
}

export interface InsightsResponse {
  period: string;
  check_ins: number;
  active_days: number;
  top_mood: string | null;
  mood_breakdown: { mood: string; count: number }[];
  by_source: Record<string, number>;
  trend: "improving" | "dipping" | "steady" | "not enough data";
  observations: string[];
  generated_by: string;
}

export type MatchTopic = "work_study" | "relationships" | "family" | "health" | "loneliness" | "other";
export type MatchSupportStyle = "just_listen" | "share_experience" | "give_advice" | "light_distraction";
export type MatchGoal = "feel_heard" | "feel_less_alone" | "get_practical_tips" | "laugh_a_bit";

export interface MatchAnswers {
  mood: SoloEmotion;
  topic: MatchTopic;
  support_style: MatchSupportStyle;
  goal: MatchGoal;
}

export interface MatchSession {
  session_id: string;
  my_alias: string;
  peer_alias: string;
  status: "active" | "ended";
  created_at: string;
}

export interface MatchStateResponse {
  status: "idle" | "waiting" | "matched";
  session: MatchSession | null;
  waiting_since: string | null;
}

export interface MatchMessageItem {
  id: string;
  session_id: string;
  from_user_id: string;
  body: string;
  created_at: string | null;
}

export const api = {
  signup: (payload: { name: string; email: string; password: string }) =>
    request<AuthTokens>("/api/auth/signup", "POST", payload),
  login: (payload: { email: string; password: string }) =>
    request<AuthTokens>("/api/auth/login", "POST", payload),
  logout: () => request<GenericMessageResponse>("/api/auth/logout", "POST"),
  getMe: () => request<UserMe>("/api/auth/me", "GET"),
  verifyEmail: (otp: string) => request<GenericMessageResponse>("/api/auth/verify-email", "POST", { otp }),
  resendOtp: () => request<GenericMessageResponse>("/api/auth/resend-otp", "POST"),
  updateProfile: (payload: { name?: string; bio?: string }) =>
    request<UserMe>("/api/auth/profile", "PATCH", payload),
  uploadAvatar: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<{ avatar_url: string }>("/api/auth/avatar", "POST", form, true);
  },
  discoverUsers: (limit = 24) => request<DiscoverUser[]>(`/api/connection/discover?limit=${limit}`, "GET"),

  detectEmotion: (payload: { image_base64: string; reason?: string }) =>
    request<EmotionResponse>("/api/emotion/detect", "POST", payload),
  attachEmotionReason: (payload: { emotion_id: string; text: string }) =>
    request<{ message: string; reason: string | null }>("/api/emotion/attach-reason", "POST", payload),
  sendChat: (payload: { message: string; emotion_context?: string; mode?: ChatMode }) =>
    request<ChatResponse>("/api/chat/send", "POST", payload),
  getChatHistory: () => request<ChatHistoryResponse>("/api/chat/history", "GET"),
  clearChat: () => request<GenericMessageResponse>("/api/chat/clear", "POST"),

  joinCommunity: (community_name: string) =>
    request<GenericMessageResponse>("/api/community/join", "POST", { community_name }),
  getCommunityDetails: (community_name: string) =>
    request<CommunityDetails>(`/api/community/details/${encodeURIComponent(community_name)}`, "GET"),
  getCommunityFeed: (limit = 30) =>
    request<CommunityFeedResponse>(`/api/community/feed?limit=${limit}`, "GET"),
  createCommunityPost: (text: string) =>
    request<CommunityPost>("/api/community/post", "POST", { text }),
  likeCommunityPost: (post_id: string) =>
    request<GenericMessageResponse>("/api/community/like", "POST", { post_id }),
  commentCommunityPost: (post_id: string, text: string) =>
    request<GenericMessageResponse>("/api/community/comment", "POST", { post_id, text }),
  /** Sends a request; the other user must accept before you can chat. */
  sendConnectionRequest: (payload: { target_user_email?: string; target_user_id?: string }) =>
    request<GenericMessageResponse>("/api/connection/request", "POST", payload),
  getConnectionState: () => request<ConnectionStateResponse>("/api/connection/state", "GET"),
  acceptConnection: (request_id: string) =>
    request<GenericMessageResponse>("/api/connection/accept", "POST", { request_id }),
  rejectConnection: (request_id: string) =>
    request<GenericMessageResponse>("/api/connection/reject", "POST", { request_id }),
  searchUsers: (q: string) =>
    request<PublicUser[]>(
      `/api/connection/users/search?q=${encodeURIComponent(q)}`,
      "GET",
    ),
  getDirectMessages: (peerUserId: string, limit = 80) =>
    request<DirectMessageItem[]>(
      `/api/connection/messages/${encodeURIComponent(peerUserId)}?limit=${limit}`,
      "GET",
    ),
  /** @deprecated use sendConnectionRequest — kept for compatibility */
  addConnection: (target_user_email: string) =>
    request<GenericMessageResponse>("/api/connection/add", "POST", { target_user_email }),

  submitFeedback: (payload: {
    flow_type: "with_flow" | "without_flow";
    content_type?: "quotes" | "exercises" | "videos" | null;
    message: string;
    rating: number;
  }) => request<FeedbackResponse>("/api/feedback/submit", "POST", payload),

  soloAnalyze: (payload: { text: string; session_id?: string | null }) =>
    request<SoloAnalyzeResponse>("/api/solo/analyze", "POST", payload),

  getInsights: (range: "week" | "month" = "month") =>
    request<InsightsResponse>(`/api/insights/summary?range=${range}`, "GET"),

  startMatch: (answers: MatchAnswers) => request<MatchStateResponse>("/api/match/start", "POST", answers),
  getMatchState: () => request<MatchStateResponse>("/api/match/state", "GET"),
  cancelMatch: () => request<GenericMessageResponse>("/api/match/cancel", "POST"),
  getMatchMessages: (sessionId: string, limit = 100) =>
    request<MatchMessageItem[]>(`/api/match/messages/${encodeURIComponent(sessionId)}?limit=${limit}`, "GET"),
  revealMatch: (sessionId: string) =>
    request<GenericMessageResponse>("/api/match/reveal", "POST", { session_id: sessionId }),
  endMatch: (sessionId: string) =>
    request<GenericMessageResponse>("/api/match/end", "POST", { session_id: sessionId }),
  reportMatch: (sessionId: string, reason: string) =>
    request<GenericMessageResponse>("/api/match/report", "POST", { session_id: sessionId, reason }),
};
