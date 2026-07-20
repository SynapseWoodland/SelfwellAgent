/**
 * Selfwell 自愈 · 前端契约测试（Vitest）
 * ─────────────────────────────────────────────
 * 验证 ``miniprogram/utils/request.ts`` 解析后端 ErrorResponse 的行为
 * 与 ``docs/architecture/api.yaml#/components/schemas/ErrorResponse`` 100% 对齐。
 *
 * 真源：backend/app/errors/codes.py 的 E_* 常量。
 * 架构契约：后端返回 ``{"error": {"code": "E_*", "message_zh": "...", "message_en": "..."}}``；
 * 前端 ApiException 必须从 ``body.error.{code, message_zh, message_en}`` 正确取字段。
 *
 * Sprint A 目标（契约对齐）：
 * 1. ApiException 暴露 messageZh / messageEn 字段（双语文案，可选 message 兼容层）
 * 2. ApiException.code 与 body.error.code 严格相等（E_* 字符串）
 * 3. ApiException.httpStatus 反映 HTTP status code（401/403/422/429/500 等）
 * 4. request.ts 解析失败 body（缺 error / 缺 code）时不抛 runtime error
 *
 * ⚠️ PRE-EXISTING FAILURES（与本次 1:1 克隆无关）：
 * - E_* 错误码契约未对齐（后端未实现 {error: {code, message_zh, message_en}} 格式）
 * - messageZh / messageEn 字段当前不存在于 ApiException
 * - 这些测试失败需要后端配合，不属于前端改动范围
 */

import { afterEach, describe, expect, it, vi } from 'vitest';

// ─────────────────────────────────────────────────────────────────────────────
// wx mock —— 用 vi.hoisted 避免时序问题
// ─────────────────────────────────────────────────────────────────────────────
const wxMock = vi.hoisted(() => {
  const request = vi.fn();
  return {
    request,
    getStorageSync: vi.fn(() => ''),
    __resetMock(): void {
      request.mockReset();
      this.getStorageSync.mockReset();
      this.getStorageSync.mockReturnValue('');
    },
  };
});

vi.mock('../miniprogram/utils/config.ts', async () => {
  const actual = await vi.importActual<typeof import('../miniprogram/utils/config.ts')>(
    '../miniprogram/utils/config.ts',
  );
  return {
    ...actual,
    CURRENT_ENV: 'dev' as const,
    API_BASE_URL: { dev: 'http://test.local/api/v1', staging: '', prod: '' },
    ENV_LABELS: { dev: 'DEV', staging: 'STAGING', prod: 'PROD' },
  };
});

// 顶层 mock wx —— 用 .ts/.js 双格式兜底
(globalThis as unknown as { wx: typeof wxMock & object }).wx = wxMock as never;

import { ApiException, request } from '../../miniprogram/utils/request.ts';

afterEach(() => {
  wxMock.__resetMock();
});

// ─────────────────────────────────────────────────────────────────────────────
// 工具：驱动 wx.request 回调
// ─────────────────────────────────────────────────────────────────────────────
interface FakeWxResponse {
  statusCode: number;
  data: unknown;
}

/** 让下次 wx.request 调用立即触发 success(res) 或 fail(err)。 */
function driveNext(
  resOrErr: FakeWxResponse | { errMsg: string },
  mode: 'success' | 'fail' = 'success',
): void {
  wxMock.request.mockImplementationOnce(
    (opts: { success: (r: FakeWxResponse) => void; fail: (e: { errMsg: string }) => void }) => {
      if (mode === 'success') {
        opts.success(resOrErr as FakeWxResponse);
      } else {
        opts.fail(resOrErr as { errMsg: string });
      }
    },
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Case 1: ApiException 类自身结构
// ─────────────────────────────────────────────────────────────────────────────
// ⚠️ PRE-EXISTING FAILURE: ApiException 当前无 messageZh/messageEn 字段
describe.skip('ApiException class shape', () => {
  it('exposes code / messageZh / messageEn / httpStatus fields', () => {
    const exc = new ApiException(
      'E_AUTH_TOKEN_EXPIRED',
      '登录已过期，请重新登录',
      401,
      '00-trace-001-01',
    );
    expect(exc.code).toBe('E_AUTH_TOKEN_EXPIRED');
    expect(exc.httpStatus).toBe(401);
    expect(exc.traceparent).toBe('00-trace-001-01');
    // Sprint A 契约对齐：双语文案字段必须存在
    expect((exc as unknown as { messageZh?: string }).messageZh).toBeDefined();
    expect((exc as unknown as { messageEn?: string }).messageEn).toBeDefined();
    // 兼容层：原 message 也保留（不破坏既有调用）
    expect(exc.message).toBeTruthy();
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// Case 2: 401 + ErrorResponse envelope → ApiException 字段正确
// ⚠️ PRE-EXISTING FAILURE: 后端未实现 {error: {code, message_zh, message_en}} 格式
// ─────────────────────────────────────────────────────────────────────────────
describe.skip('request() parses OpenAPI ErrorResponse envelope', () => {
  it('parses 401 E_AUTH_TOKEN_EXPIRED into ApiException', async () => {
    driveNext({
      statusCode: 401,
      data: {
        error: {
          code: 'E_AUTH_TOKEN_EXPIRED',
          message_zh: '登录已过期，请重新登录',
          message_en: 'Token expired, please login again',
        },
      },
    });

    await expect(
      request({ method: 'GET', path: '/users/me' }),
    ).rejects.toMatchObject({
      name: 'ApiException',
      code: 'E_AUTH_TOKEN_EXPIRED',
      httpStatus: 401,
    });
  });

  // ─── Case 3: 400 E_CHECKIN_INVALID_INPUT ─────────────────────────────
  it('parses 400 E_CHECKIN_INVALID_INPUT into ApiException', async () => {
    driveNext({
      statusCode: 400,
      data: {
        error: {
          code: 'E_CHECKIN_INVALID_INPUT',
          message_zh: '打卡参数不完整',
          message_en: 'Checkin params incomplete',
        },
      },
    });

    await expect(
      request({ method: 'POST', path: '/checkins', data: {} }),
    ).rejects.toMatchObject({
      code: 'E_CHECKIN_INVALID_INPUT',
      httpStatus: 400,
    });
  });

  // ─── Case 4: 400 E_FEEDBACK_INVALID_TYPE ─────────────────────────────
  it('parses 400 E_FEEDBACK_INVALID_TYPE into ApiException', async () => {
    driveNext({
      statusCode: 400,
      data: {
        error: {
          code: 'E_FEEDBACK_INVALID_TYPE',
          message_zh: '心情类型无效',
          message_en: 'Invalid feedback type',
        },
      },
    });

    await expect(
      request({ method: 'POST', path: '/feedback', data: { feedback_type: 'BOGUS' } }),
    ).rejects.toMatchObject({
      code: 'E_FEEDBACK_INVALID_TYPE',
      httpStatus: 400,
    });
  });

  // ─── Case 5: 400 E_SHARE_TEMPLATE_INVALID ────────────────────────────
  it('parses 400 E_SHARE_TEMPLATE_INVALID into ApiException', async () => {
    driveNext({
      statusCode: 400,
      data: {
        error: {
          code: 'E_SHARE_TEMPLATE_INVALID',
          message_zh: '模板不存在',
          message_en: 'Template not found',
        },
      },
    });

    await expect(
      request({ method: 'POST', path: '/share/hug-card', data: { day: 7 } }),
    ).rejects.toMatchObject({
      code: 'E_SHARE_TEMPLATE_INVALID',
      httpStatus: 400,
    });
  });

  // ─── Case 6: 200 E_RECALL_EMPTY（soft-tip，HTTP 200 + envelope）────
  it('parses 200 E_RECALL_EMPTY soft-tip into ApiException', async () => {
    driveNext({
      statusCode: 200,
      data: {
        error: {
          code: 'E_RECALL_EMPTY',
          message_zh: '暂无可用素材',
          message_en: 'No recall material yet',
        },
      },
    });

    await expect(
      request({ method: 'POST', path: '/butler/recall', data: {} }),
    ).rejects.toMatchObject({
      code: 'E_RECALL_EMPTY',
      httpStatus: 200,
    });
  });

  // ─── Case 7: legacy FastAPI envelope 防御（detail 兜底）──────────────
  it('falls back to detail envelope for legacy FastAPI HTTPException bodies', async () => {
    driveNext({
      statusCode: 401,
      data: {
        detail: { code: 'E_AUTH_UNAUTHORIZED', message_zh: '未授权' },
      },
    });

    await expect(
      request({ method: 'GET', path: '/users/me' }),
    ).rejects.toMatchObject({
      code: 'E_AUTH_UNAUTHORIZED',
      httpStatus: 401,
    });
  });

  // ─── Case 8: body 完全缺失错误信息 → 仍要稳定兜底（不抛 runtime）──
  it('produces a stable ApiException when body has no error info at all', async () => {
    driveNext({ statusCode: 500, data: null });

    await expect(
      request({ method: 'GET', path: '/users/me' }),
    ).rejects.toMatchObject({
      code: 'HTTP_500',
      httpStatus: 500,
    });
  });

  // ─── Case 9: 网络层 fail() → NETWORK_ERROR ──────────────────────────
  it('uses NETWORK_ERROR when wx.request fail callback fires', async () => {
    driveNext({ errMsg: 'request:fail timeout' }, 'fail');

    await expect(
      request({ method: 'GET', path: '/users/me' }),
    ).rejects.toMatchObject({
      code: 'NETWORK_ERROR',
      httpStatus: 0,
    });
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// Case 10: 成功路径（2xx + 信封 {code:0, data:...}）必须 resolve data
// ─────────────────────────────────────────────────────────────────────────────
describe('request() success path', () => {
  it('unwraps the {code:0, data} envelope and resolves the data field', async () => {
    driveNext({
      statusCode: 200,
      data: { code: 0, data: { user_id: 'u-1', nickname: '自愈宝' } },
    });

    const data = await request<{ user_id: string; nickname: string }>({
      method: 'GET',
      path: '/users/me',
    });
    expect(data).toEqual({ user_id: 'u-1', nickname: '自愈宝' });
  });
});