/**
 * Selfwell · 共享 DTO 类型（页内）
 * ──────────────────────────────────────────────────
 * 真实项目应有 packages/api-types/ts/，但 monorepo 化尚未落地；
 * 在 types/api.d.ts 中以本文件为唯一定义，被所有 page / component 引用。
 *
 * 字段名严格对齐 docs/api/openapi.yaml V1.1.0；变更前必须 PR 至 §17.10 接口冻结窗口外。
 *
 * 重大约定：
 *  - 用户标识：user_id_pseudo（后端给前端用的伪 ID，§17.10）
 *  - 推送 payload：traceparent + client_platform + user_id_pseudo（§17.17）
 *  - ID 类型用 string（雪花 / uuidv4），数值用 number
 */

export type ISODateTime = string;
export type ISODate = string;
export type ClientPlatform = 'wechat_mp' | 'flutter_app';

/* ─────────── 通用响应壳 ─────────── */

export interface ApiOk<T> {
  ok: true;
  data: T;
}
export interface ApiErr {
  ok: false;
  code: string;
  message: string;
  detail?: unknown;
  traceparent?: string;
}
export type ApiResp<T> = ApiOk<T> | ApiErr;

export interface Paginated<T> {
  items: T[];
  page: number;
  pageSize: number;
  total: number;
}

/* ─────────── M1 用户 / 登录 ─────────── */

// 后端 v1 WxLoginRequest 字段名
export interface WxLoginReq {
  code: string;
  client?: 'wx_mp' | 'ios' | 'android' | 'harmony';
  user_profile?: { nickname?: string; avatar?: string } | null;
}
export interface WxLoginData {
  user_id: string;
  access_token: string;
  expires_in: number;
  is_new_user: boolean;
  user_status: string;
}
export interface WxLoginResp {
  code: number;
  data: WxLoginData;
}

export interface UserMe {
  user_id_pseudo: string;
  nickname: string;
  avatar_url: string;
  registered_at: ISODateTime;
  current_streak_days: number;
  /** 个性化提示语冷却截止（避免打扰） */
  persona_quiet_until?: ISODateTime;
}

/* ─────────── M3 21 天方案 / M4 打卡 ─────────── */

export interface TodayPlan {
  plan_id: string;
  day_index: number; // 1..21
  total_days: number;
  tasks: TodayTask[];
}

export interface TodayTask {
  task_id: string;
  title: string;
  subtitle: string;
  video_id?: string;
  video_url?: string;
  cover_url?: string;
  duration_sec: number;
  body_part_tags: string[];
  done: boolean;
}

export interface CheckinToday {
  date: ISODate;
  total: number;
  done: number;
  percent: number;
  /** 当日已完成项的 task_id 列表 */
  done_task_ids: string[];
}

export interface CreateCheckinReq {
  date: ISODate;
  task_ids: string[];
  /** 附带的反馈文本，可选 */
  mood_text?: string;
}
export interface CreateCheckinResp {
  checkin_id: string;
  new_streak: number;
  ack_text: string; // 来自 ack-pool.yaml
}

/* ─────────── M2 智能分析 / SSE ─────────── */

export interface PresignReq {
  mime_type: 'image/jpeg' | 'image/png' | 'image/webp';
  byte_size: number;
  purpose?: 'diagnosis' | 'feedback';
}
export interface PresignResp {
  /** 表单 POST 目标 URL */
  form_url: string;
  /** 签名字段 dict（含 key 字段）；前端拼 multipart 时直接作为 formData 传入 */
  form_fields: Record<string, string>;
  object_key: string;
  expires_in?: number;
  cdn_url?: string;
  /** 已废弃：保留向后兼容（请用 form_url + form_fields） */
  upload_url?: string;
}

/** 单张诊断照片（向后兼容 v1 + v2）
 *
 * v1（@deprecated）：仅 ``url``。
 * v2：``object_key`` + ``body_part`` + ``format`` + ``size_bytes``，后端用 presigned_get_url 解析。
 */
export interface PhotoInput {
  /** 公开可访问 URL（v1 兼容） */
  url?: string;
  /** 对象 key（v2 推荐） */
  object_key?: string;
  body_part: 'face' | 'head' | 'shoulder_neck';
  format?: 'jpg' | 'png' | 'webp' | 'heic';
  size_bytes?: number;
}

export interface CreateDiagnosisReq {
  /** 多图版本（与 v1 单图互斥） */
  photos?: PhotoInput[];
  /** v1 单图字段（保留向后兼容） */
  body_image_key?: string;
  objectKey?: string;
  /** 用户备注 */
  user_note?: string;
  complaint?: string;
  /** PR-A4：A 场景切换到异步 Job 模式（POST /diagnosis?async=true 时携带） */
  async?: boolean;
}

export type DiagnosisPhase =
  | 'preprocess'
  | 'body_detect'
  | 'tag_extract'
  | 'video_match'
  | 'plan_draft'
  | 'harm_review'
  | 'finalize'
  | 'done';

export interface DiagnosisSseEvent {
  phase: DiagnosisPhase;
  progress: number; // 0..100
  payload?: unknown;
  /** 部分更新（增量输出） */
  partial_text?: string;
}

// ─────────────────────────────────────────────────
// 诊断 Job 异步模式（与后端 POST /diagnosis?async=true 契约）
// PR-A4 — 小程序侧承接；后端 PR-A2 PR-A1 落地后此契约生效
// ─────────────────────────────────────────────────
export interface DiagnosisJob {
  job_id: string;
  status: 'queued' | 'running' | 'ready' | 'failed';
  stream_url: string;
}

// ─────────────────────────────────────────────────
// SSE 事件 payload（GET /diagnosis/jobs/{id}/stream）
// ─────────────────────────────────────────────────
export type SseEventName = 'stage' | 'done' | 'error';

export interface SseStagePayload {
  stage: 'connected' | 'preprocess' | 'analyzing' | 'suggestion' | 'ready';
  percent: number;          // 0..100
  message: string;          // 中文文案
  ok: boolean;
  report_id?: string;       // 仅 stage=ready 携带
}

export interface SseDonePayload {
  report_id: string;
}

export interface SseErrorPayload {
  code: string;
  message_zh: string;
  stage?: string;
}

// ─────────────────────────────────────────────────
// Plan 视图：?view=all 响应契约
// ─────────────────────────────────────────────────
export type PlanDayState = 'done' | 'today' | 'locked';

export interface PlanDayCell {
  day: number;          // 1..21
  state: PlanDayState;
  tasks_count: number;   // 1..3
  phase: 1 | 2 | 3;
}

export interface PlanWeek {
  week_no: 1 | 2 | 3;
  title: string;         // 第一阶段 · 习惯启动 / ...
  days: PlanDayCell[];   // length=7
}

export interface PlanAllViewData {
  plan_id: string;
  total_days: 21;
  started_at: string;    // YYYY-MM-DD
  current_day_index: number;  // 1..21
  view: 'all';
  weeks: PlanWeek[];     // length=3
}

// 兼容老 schema；同时为 directions[] 提供一个内层类型
export interface DiagnosisDirection {
  title: string;
  description: string;
  video_url?: string;
}

export interface DiagnosisReport {
  diagnosis_id: string;
  user_id_pseudo: string;
  created_at: ISODateTime;
  tags: string[]; // 来自 §4 body-parts.yaml
  tag_scores: Record<string, number>;
  report_text: string;
  matched_video_ids: string[];
  recommended_plan_id?: string;
  /** PR-A4：A 场景 GET /diagnosis/{id} 新契约方向列表 */
  directions?: DiagnosisDirection[];
  /** PR-A4：报告摘要（页面顶部文案） */
  summary?: string;
  /** PR-A4：LLM 模型标识（埋点/审计用） */
  llm_model?: string;
}

/* ─────────── M5 智能管家 ─────────── */

export type PersonaState = 'greeting' | 'listening' | 'thinking' | 'answer';

/**
 * SSE `end` 帧 data 结构（PR-A2 worker Y 落地：on end 整体落库后回写 ai_messages.id）。
 * - 由 assistant-home 消费；types 层只补定义，runtime cast 不动。
 * - ai_messages.id 是 UUID（128 位），超 JS Number 53 位精度 → 必须 string，**不要**改回 number。
 */
export type AssistantSseEndData = {
  ok: boolean;
  reply?: string;
  persona_state?: string;
  medical_guarded?: boolean;
  /** end 帧整条落库后返回的 ai_messages.id；UUID 序列化字符串（PR-A2 decision B） */
  ai_msg_id?: string;
};

export interface AssistantSession {
  session_id: string;
  user_id_pseudo: string;
  state: PersonaState;
  created_at: ISODateTime;
  last_active_at: ISODateTime;
}

export interface AssistantMessage {
  message_id: string;
  session_id: string;
  role: 'user' | 'assistant' | 'system';
  text: string;
  /** 对于 persona 状态机使用 */
  state?: PersonaState;
  created_at: ISODateTime;
}

/**
 * V5.2.1-PR5 · 6 字段用户档案（snake_case，与后端 User ORM + assistant_profile JSONB 对齐）。
 *
 * 真源：SPEC-V521-PR5-frontend-contract.md §FR-5 + utils/profile-storage.ts。
 *
 * 6 字段：
 *  - age_range: 年龄段（"18-29" / "30-39" / "40-49" / "50+"，与 profile 页 picker 一致）
 *  - sitting_hours: 每日久坐小时数（0-24）
 *  - focus_parts: 重点关注部位（["面部","肩颈"]，与后端 body_part 白名单对齐）
 *  - intensity: 干预强度（"轻柔" / "标准" / "强效"）
 *  - preferred_time: 偏好干预时段（"早上" / "中午" / "晚上"）
 *  - skin_type: 肤质（"油性" / "干性" / "中性" / "混合" / "敏感"）
 *
 * 与 utils/profile-storage.ts 中的 `UserProfile6Fields` **保持字段一致**；
 * 这里再次定义是因为 types 层是 DTO 单源（避免 utils 改动直接影响 DTO 类型）。
 */
export interface UserProfile6Fields {
  age_range?: string | null;
  sitting_hours?: number | null;
  focus_parts?: string[] | null;
  intensity?: string | null;
  preferred_time?: string | null;
  skin_type?: string | null;
}

/**
 * V5.2.1-PR5 · assistant-home runSmartAnalyze SSE body 契约。
 *
 * 与后端 `POST /assistant/sessions/{id}/messages` body 字段对齐（`assistant_v1.py`）；
 * `profile` 字段由前端 utils/profile-storage.ts 读 storage 拼装，全 null 时省略。
 */
export interface SendAssistantMessageBody {
  text: string;
  image_keys?: string[] | null;
  body_parts?: string[] | null;
  profile?: UserProfile6Fields | null;
}

export interface SendAssistantMessageReq {
  text: string;
  client_platform: ClientPlatform;
  traceparent?: string;
}
export interface SendAssistantMessageResp {
  assistant_message: AssistantMessage;
  next_state: PersonaState;
}

/* ─────────── M7 反馈 / 心情日记 / ACK 池 ─────────── */

export type AckTone = 'warm' | 'neutral' | 'celebrate';

/** 单条 ACK 条目（来自 docs/data/ack-pool.yaml） */
export interface AckEntry {
  id: string;
  text: string; // 30 字内
  tone: AckTone;
  forbidden?: boolean; // 来自 ack-pool.yaml 的 forbidden 段，渲染必跳
}

export interface CreateMoodReq {
  feedback_type: 'mood_text' | 'mood_photo' | 'skin_photo';
  text_content?: string;
  photo_url?: string;
  photo_size_bytes?: number;
  body_part?: string;
}
export interface CreateMoodResp {
  feedback_id: string;
  ack: AckEntry; // 后端从 ack-pool.yaml 选取
}

/* ─────────── M6 蜕变广场 ─────────── */

export interface CommunityPost {
  post_id: string;
  user_id_pseudo: string;
  nickname: string;
  avatar_url: string;
  content: string;
  image_keys: string[];
  like_count: number;
  reply_count: number;
  created_at: ISODateTime;
  /** 是否已点赞 */
  liked_by_me: boolean;
}

export interface ListPostsReq {
  page: number;
  page_size: number;
  sort?: 'latest' | 'hot';
}
export interface ListPostsResp {
  items: CommunityPost[];
  page: number;
  page_size: number;
  total: number;
}

/* ─────────── M8 主动回忆 ─────────── */

export type RecallDay = 7 | 14 | 21;

export interface RecallCompareResp {
  day: RecallDay;
  user_id_pseudo: string;
  baseline_image_key: string;     // D-7/14/21 之前
  current_image_key: string;       // 当下
  baseline_report_text: string;
  current_report_text: string;
  diff_tags: string[]; // 变更的 §4 tags
  summary_text: string;
  generated_at: ISODateTime;
}

/* ─────────── M10 抱抱卡 ─────────── */

export interface HugCardReq {
  day: RecallDay;
  /** 'canvas' = 客户端 canvas-2d，'server' = PIL 兜底 */
  render_mode?: 'canvas' | 'server';
}
export interface HugCardResp {
  image_url: string;          // 750×1000 长图
  share_text: string;
  template_id: string;
  expires_at: ISODateTime;
}

/* ─────────── M9 推送 / 订阅 ─────────── */

export type WxTemplateId =
  | 'checkin_remind'
  | 'recall_card'
  | 'plan_milestone'
  | 'community_reply';

export interface PushSubscribeReportReq {
  client_platform: ClientPlatform;
  user_id_pseudo: string;
  traceparent?: string;
  results: Array<{
    template_id: WxTemplateId;
    status: 'accept' | 'reject' | 'ban' | 'filter' | 'unknown';
  }>;
}
export interface PushSubscribeReportResp {
  ok: boolean;
  server_received_at: ISODateTime;
}

/* ─────────── 通用错误码（精简版，与 docs/api/error-codes.md 对齐） ─────────── */

export const E_USER_INVALID_INPUT = 'E_USER_INVALID_INPUT';
export const E_AUTH_WX_CODE_INVALID = 'E_AUTH_WX_CODE_INVALID';
export const E_AUTH_TOKEN_EXPIRED = 'E_AUTH_TOKEN_EXPIRED';
export const E_PLAN_NOT_FOUND = 'E_PLAN_NOT_FOUND';
export const E_DIAGNOSIS_IN_PROGRESS = 'E_DIAGNOSIS_IN_PROGRESS';
export const E_DIAGNOSIS_NOT_FOUND = 'E_DIAGNOSIS_NOT_FOUND';
export const E_FORBIDDEN_MEDICAL = 'E_FORBIDDEN_MEDICAL';
export const E_ACK_NOT_FOUND = 'E_ACK_NOT_FOUND';
export const E_RATE_LIMIT = 'E_RATE_LIMIT';
export const E_INTERNAL = 'E_INTERNAL';
