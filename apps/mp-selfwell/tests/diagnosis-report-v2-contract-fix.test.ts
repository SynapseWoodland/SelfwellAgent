import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

const read = (name: string) => readFileSync(
  join(__dirname, '..', 'miniprogram', 'pages', 'diagnosis-report-v2', name),
  'utf-8',
);

describe('PR-Contract-Fix C-2 · diagnosis-report-v2 调 POST /plans/generate + report_id', () => {
  it('AC-1 onGeneratePlan 调 POST /plans/generate(不再调 /plans)', () => {
    const ts = read('index.ts');
    expect(ts).toMatch(/post<[^>]+>\(\s*['"]\/plans\/generate['"]/);
    expect(ts).not.toMatch(/post<[^>]+>\(\s*['"]\/plans['"]/);
  });

  it('AC-2 请求 body 含 report_id(不再用 session_id)', () => {
    const ts = read('index.ts');
    // body 必须有 report_id 字段(读 cached 或 wxmlStorage)
    expect(ts).toMatch(/report_id:\s*reportId/);
    // 不再传 session_id 给 /plans/generate
    expect(ts).not.toMatch(/session_id:\s*this\.data\.sessionId/);
  });

  it('AC-3 onGeneratePlan 跳 plan-delivery 时携带 plan_id', () => {
    const ts = read('index.ts');
    expect(ts).toContain("/pages/plan-delivery/index?plan_id=");
    expect(ts).toContain("wx.setStorageSync('plan.delivery.id'");
  });

  it('AC-4 缓存 diagnosis_v2_payload 含 report_id(从 upload 传入)', () => {
    // diagnosis-upload-v2 把后端返回的 report_id 写入 storage
    const uploadTs = readFileSync(
      join(__dirname, '..', 'miniprogram', 'pages', 'diagnosis-upload-v2', 'index.ts'),
      'utf-8',
    );
    // 必须有 report_id 写入 storage 的语句
    expect(uploadTs).toMatch(/report_id:\s*\w+/);
    expect(uploadTs).toMatch(/setStorageSync\(['"]diagnosis_v2_payload['"]/);
  });

  it('AC-5 report-v2 从 cache 读 report_id 并赋值到 data', () => {
    const ts = read('index.ts');
    // cached.report_id 要被读到 data.reportId
    expect(ts).toMatch(/cached\.report_id|cachedValue.*?report_id/);
    expect(ts).toMatch(/reportId:\s*reportId|setData\(\{[^}]*reportId/);
  });
});