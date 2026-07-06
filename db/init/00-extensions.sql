-- =============================================================================
-- 00-extensions.sql · PG 扩展 + UUID v7 函数
--   职责：PG 18+ 已内置 uuidv7()；PG 15 自带**不带** uuidv7()，需要扩展 uuid-ossp + 自定义 uuidv7 函数
--         本文件对 PG 15/18 都是幂等的
--   依据：docs/data/data-dictionary.md 附录 I §I.0.3 + 附录 G
--   执行时机：第一个启动，db init 阶段
-- =============================================================================

-- PG 15 需要显式启用 uuid-ossp（PG 18 默认开启）
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- PG 18 已内置 uuidv7()，对 PG 15 用 plpgsql 自实现（按 RFC 9562）
-- IF NOT EXISTS 在 CREATE FUNCTION 上不支持，用 DO 块做幂等
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_proc
    WHERE proname = 'uuidv7' AND pronamespace = 'public'::regnamespace
  ) THEN
    EXECUTE $f$
      CREATE OR REPLACE FUNCTION uuidv7() RETURNS uuid AS $func$
      DECLARE
        v_ts   bytea := decode(lpad(to_hex(floor(extract(epoch FROM clock_timestamp()) * 1000)::bigint), 12, '0'), 'hex');
        v_rand bytea := decode(md5(random()::text || clock_timestamp()::text), 'hex');
        v_bytes bytea;
      BEGIN
        v_bytes := v_ts || substring(v_rand from 1 for 18);
        v_bytes := set_byte(v_bytes, 6, (get_byte(v_bytes, 6) & 15)  | 112);
        v_bytes := set_byte(v_bytes, 8, (get_byte(v_bytes, 8) & 63)  | 128);
        RETURN encode(v_bytes, 'hex')::uuid;
      END;
      $func$ LANGUAGE plpgsql VOLATILE;
    $f$;
  END IF;
END
$$;

-- 时区与字符集（容器化 PG 默认 UTC + UTF8，符合字典 §0）
-- ALTER DATABASE selfwell SET timezone = 'UTC';   -- 由 docker-compose 环境变量注入
-- ALTER DATABASE selfwell SET client_encoding = 'UTF8';  -- PG 默认

-- 验证
DO $$
BEGIN
  RAISE NOTICE 'uuidv7() sample: %', uuidv7();
END
$$;