/**
 * Selfwell · 请求工具（wx.request 封装）
 * ────────────────────────────────────────
 * - baseURL 来自 utils/config.ts，不允许在 page 中硬编码
 * - 3 个拦截器：
 *     1) Auth        ：Authorization: Bearer <jwt>（jwt 来自 app.globalData.token）
 *     2) Traceparent ：透传/生成 W3C traceparent，便于与后端 OpenTelemetry 串联
 *     3) Log         ：console.log（dev/staging），prod 静默
 * - 类型 ApiException 暴露给上层做兜底 toast / 跳转登录
 *
 * 注：未启用 wx.request 的 enableHttp2/HttpDNS（基础库差异较大，留给 SF1 优化）
 */

import {
  API_BASE_URL,
  AUTH_HEADER,
  CURRENT_ENV,
  ENV_LABELS,
  REQUEST_TIMEOUT_MS,
  STORAGE_KEYS,
  TRACEPARENT_HEADER,
} from './config';

/** ApiException：业务可识别的错误（含错误码 / 错误消息） */
export class ApiException extends Error {
  public readonly code: string;
  public readonly httpStatus: number;
  public readonly traceparent?: string;

  constructor(
    code: string,
    message: string,
    httpStatus: number,
    traceparent?: string,
  ) {
    super(message);
    this.name = 'ApiException';
    this.code = code;
    this.httpStatus = httpStatus;
    this.traceparent = traceparent;
  }
}

/** 请求参数（与 wx.request 保持一致，外加泛型 T） */
export interface RequestOptions<TReq = unknown> {
  method: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
  path: string;
  data?: TReq;
  /** 自定义 header（会与 Auth/Traceparent 合并） */
  header?: Record<string, string>;
  /** 是否跳过 Auth 拦截器（默认 false） */
  skipAuth?: boolean;
  /** 是否跳过 Traceparent 拦截器（默认 false） */
  skipTraceparent?: boolean;
  /** 是否跳过 Log 拦截器（默认 false） */
  skipLog?: boolean;
  /** 自定义超时（ms），不传则用 REQUEST_TIMEOUT_MS */
  timeoutMs?: number;
}

/** 后端统一错误体（参考 docs/api/error-codes.md） */
interface ApiErrorBody {
  code: string;
  message: string;
  detail?: unknown;
}

/** 解析 traceparent（保留原值，缺失则新生成） */
function buildTraceparent(): string {
  // 00-<trace-id 32 hex>-<parent-id 16 hex>-<flags 2 hex>
  const hex = '0123456789abcdef';
  const seg = (n: number) => {
    let s = '';
    for (let i = 0; i < n; i++) s += hex[(Math.random() * 16) | 0];
    return s;
  };
  return `00-${seg(32)}-${seg(16)}-01`;
}

/**
 * 统一请求入口
 * @example
 *   const user = await request<{ userId: string }>({ method: 'GET', path: '/users/me' });
 */
export function request<TRes = unknown, TReq = unknown>(
  opts: RequestOptions<TReq>,
): Promise<TRes> {
  const baseURL = API_BASE_URL[CURRENT_ENV];
  const url = baseURL + opts.path;
  const header: Record<string, string> = { ...(opts.header ?? {}) };

  // 拦截器 1: Auth
  if (!opts.skipAuth) {
    const jwt = wx.getStorageSync(STORAGE_KEYS.jwt);
    if (jwt) header[AUTH_HEADER] = `Bearer ${jwt}`;
  }

  // 拦截器 2: Traceparent
  let tp: string | undefined;
  if (!opts.skipTraceparent) {
    tp = header[TRACEPARENT_HEADER] ?? buildTraceparent();
    header[TRACEPARENT_HEADER] = tp;
  }

  // 拦截器 3: Log（仅 dev/staging 打印）
  if (!opts.skipLog && CURRENT_ENV !== 'prod') {
    console.log(
      `[${ENV_LABELS[CURRENT_ENV]} request]`,
      opts.method,
      url,
      opts.data ?? '',
    );
  }

  return new Promise<TRes>((resolve, reject) => {
    wx.request({
      url,
      method: opts.method,
      data: opts.data as wx.RequestDataOption | undefined,
      header,
      timeout: opts.timeoutMs ?? REQUEST_TIMEOUT_MS,
      success: (res) => {
        const status = res.statusCode;
        const body = res.data as unknown;
        if (status >= 200 && status < 300) {
          resolve(body as TRes);
          return;
        }
        const errBody = (body ?? {}) as Partial<ApiErrorBody>;
        reject(
          new ApiException(
            errBody.code ?? `HTTP_${status}`,
            errBody.message ?? `HTTP ${status}`,
            status,
            tp,
          ),
        );
      },
      fail: (err) => {
        // 网络层错误（超时 / 断网 / 跨域）—— 用稳定错误码
        reject(
          new ApiException(
            'NETWORK_ERROR',
            err.errMsg ?? '网络异常，请稍后重试',
            0,
            tp,
          ),
        );
      },
    });
  });
}

/** 便捷方法 */
export const get = <TRes = unknown>(path: string, header?: Record<string, string>) =>
  request<TRes>({ method: 'GET', path, header });

export const post = <TRes = unknown, TReq = unknown>(
  path: string,
  data?: TReq,
  header?: Record<string, string>,
) => request<TRes, TReq>({ method: 'POST', path, data, header });

export const put = <TRes = unknown, TReq = unknown>(
  path: string,
  data?: TReq,
  header?: Record<string, string>,
) => request<TRes, TReq>({ method: 'PUT', path, data, header });

export const del = <TRes = unknown>(path: string, header?: Record<string, string>) =>
  request<TRes>({ method: 'DELETE', path, header });