"""Idempotency + structural validation tests for alembic 0007 (V2 IA 4 tables).

True source: ``plans/v2-unified-parent.md`` §2.2 + IA V2.2 §2A.2 + alembic 0007.

Why this test exists
--------------------
The existing 0002 migration runs ``SELECT ... FROM reports WHERE deleted_at IS NULL``
in its upgrade body, which fails when alembic is invoked in offline (``--sql``) mode
without a real DB. We can't use the standard alembic dry-run chain here. Instead,
we directly invoke ``0007.upgrade()`` / ``0007.downgrade()`` against a fake
``alembic.op`` so we can:

1. Prove upgrade() and downgrade() both execute without exceptions (idempotent
   callable check).
2. Enumerate every CREATE TABLE / CREATE INDEX / CONSTRAINT produced by 0007 so
   that any future field / index / constraint change is caught here.
3. Cover the regression risk of removing a V2 table accidentally.

Each assertion maps 1:1 to a clause in IA V2.2 §2A.2.x.
"""
from __future__ import annotations

import importlib.util
import sys
import types
from collections.abc import Iterator


def _load_0007_with_mocked_op() -> tuple[object, dict[str, list[object]]]:
    """Load 0007 module with a fake ``alembic.op`` that captures every call.

    Returns:
        (module, captured) where ``captured`` is a dict mapping operation name
        to a list of captured arguments (each argument a tuple of positional args).
    """
    sys.path.insert(0, "D:/agent-project/SelfwellAgent/.venv/Lib/site-packages")
    sys.path = [p for p in sys.path if not p.endswith("backend") or "site-packages" in p]

    captured: dict[str, list[object]] = {
        "create_table": [],
        "create_index": [],
        "drop_table": [],
        "drop_index": [],
    }

    def fake_create_table(name, *columns, **kwargs):
        captured["create_table"].append((name, columns, kwargs))

    def fake_create_index(name, table, columns, **kw):
        captured["create_index"].append((name, table, columns))

    def fake_drop_table(name, **kw):
        captured["drop_table"].append((name, kw))

    def fake_drop_index(name, table=None, **kw):
        captured["drop_index"].append((name, table, kw))

    fake_op = types.ModuleType("fake_op_for_0007_test")
    fake_op.create_table = fake_create_table
    fake_op.create_index = fake_create_index
    fake_op.drop_table = fake_drop_table
    fake_op.drop_index = fake_drop_index

    sys.modules["alembic"] = types.ModuleType("alembic")
    sys.modules["alembic.op"] = fake_op

    spec = importlib.util.spec_from_file_location(
        "mig_0007",
        "D:/agent-project/SelfwellAgent/backend/alembic/versions/0007_add_v2_ia_tables.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, captured


def _reset_op_capture(captured: dict[str, list[object]]) -> None:
    """Clear captured dict in place before invoking upgrade() / downgrade()."""
    for k in captured:
        captured[k].clear()


def _iter_constraint_objects(table_args: tuple[object, ...]) -> Iterator[object]:
    """Yield Constraint objects (UC / PK / CHECK) from positional ``columns`` of op.create_table."""
    for c in table_args:
        cls_name = type(c).__name__
        if cls_name in ("UniqueConstraint", "PrimaryKeyConstraint", "CheckConstraint"):
            yield c


def test_0007_revision_metadata() -> None:
    """0007 是 0006_add_skin_type_to_users 的下游；rev / down_rev 写对。"""
    module, _ = _load_0007_with_mocked_op()
    assert module.revision == "0007_add_v2_ia_tables"
    assert module.down_revision == "0006_add_skin_type_to_users"
    assert callable(module.upgrade)
    assert callable(module.downgrade)


def test_0007_creates_four_v2_tables() -> None:
    """IA V2.2 §2A.2: 4 张 V2 表必须在 upgrade() 中按顺序创建。"""
    module, captured = _load_0007_with_mocked_op()
    _reset_op_capture(captured)
    module.upgrade()

    table_names = [entry[0] for entry in captured["create_table"]]
    assert table_names == [
        "user_badges",
        "user_notification_prefs",
        "account_deletion_requests",
        "user_self_tags",
    ], f"Unexpected table order: {table_names}"


def test_0007_creates_seven_indexes() -> None:
    """7 个索引覆盖所有 4 张表的 user_id / 枚举 / 复合查询列。"""
    module, captured = _load_0007_with_mocked_op()
    _reset_op_capture(captured)
    module.upgrade()

    indexes = [(name, tbl, list(cols)) for name, tbl, cols in captured["create_index"]]
    expected = [
        ("ix_user_badges_user_id", "user_badges", ["user_id"]),
        ("ix_user_badges_code", "user_badges", ["code"]),
        ("ix_user_notification_prefs_user_id", "user_notification_prefs", ["user_id"]),
        ("ix_account_deletion_user_id", "account_deletion_requests", ["user_id"]),
        ("ix_account_deletion_status", "account_deletion_requests", ["status"]),
        ("ix_user_self_tags_user_id", "user_self_tags", ["user_id"]),
        ("ix_user_self_tags_user_selected", "user_self_tags", ["user_id", "is_selected"]),
    ]
    assert indexes == expected, f"Index mismatch:\n  got: {indexes}\n  exp: {expected}"


def test_0007_user_badges_unique_constraint() -> None:
    """IA V2.2 §2A.2.1: ``(user_id, code)`` 唯一约束。"""
    module, captured = _load_0007_with_mocked_op()
    _reset_op_capture(captured)
    module.upgrade()

    user_badges_entry = next(e for e in captured["create_table"] if e[0] == "user_badges")
    constraints = list(_iter_constraint_objects(user_badges_entry[1]))
    uc_names = [c.name for c in constraints if type(c).__name__ == "UniqueConstraint"]
    assert "uq_user_badges_user_code" in uc_names


def test_0007_user_notification_prefs_composite_pk() -> None:
    """IA V2.2 §2A.2.2: ``(user_id, pref_key)`` 复合主键。"""
    module, captured = _load_0007_with_mocked_op()
    _reset_op_capture(captured)
    module.upgrade()

    prefs_entry = next(e for e in captured["create_table"] if e[0] == "user_notification_prefs")
    pk_constraints = [c for c in _iter_constraint_objects(prefs_entry[1]) if type(c).__name__ == "PrimaryKeyConstraint"]
    assert len(pk_constraints) == 1
    assert pk_constraints[0].name == "pk_user_notification_prefs"


def test_0007_account_deletion_check_constraint() -> None:
    """IA V2.2 §2A.2.3: status 枚举 CHECK 约束 4 值。"""
    module, captured = _load_0007_with_mocked_op()
    _reset_op_capture(captured)
    module.upgrade()

    entry = next(e for e in captured["create_table"] if e[0] == "account_deletion_requests")
    check_constraints = [c for c in _iter_constraint_objects(entry[1]) if type(c).__name__ == "CheckConstraint"]
    assert len(check_constraints) == 1
    cc = check_constraints[0]
    assert cc.name == "ck_account_deletion_status"
    sql_text = str(cc.sqltext)
    for status in ("pending_cool_down", "confirmed", "cancelled", "executed"):
        assert status in sql_text, f"Missing status {status} in CHECK constraint: {sql_text}"


def test_0007_user_self_tags_unique_and_check() -> None:
    """IA V2.2 §2A.2.4: (user_id, tag_category, tag_value) 唯一 + 2 个 CHECK 约束。"""
    module, captured = _load_0007_with_mocked_op()
    _reset_op_capture(captured)
    module.upgrade()

    entry = next(e for e in captured["create_table"] if e[0] == "user_self_tags")
    constraints = list(_iter_constraint_objects(entry[1]))
    ucs = [c for c in constraints if type(c).__name__ == "UniqueConstraint"]
    ccs = [c for c in constraints if type(c).__name__ == "CheckConstraint"]

    assert len(ucs) == 1
    assert ucs[0].name == "uq_user_self_tags_user_category_value"

    cc_names = sorted([c.name for c in ccs])
    assert cc_names == ["ck_user_self_tags_category", "ck_user_self_tags_source"]


def test_0007_downgrade_drops_all_four_tables_in_reverse() -> None:
    """downgrade() 必须按反向顺序 drop 全部 4 表；幂等（每次调用都成功）。"""
    module, captured = _load_0007_with_mocked_op()
    _reset_op_capture(captured)
    module.downgrade()

    dropped = [e[0] for e in captured["drop_table"]]
    assert dropped == [
        "user_self_tags",
        "account_deletion_requests",
        "user_notification_prefs",
        "user_badges",
    ], f"Downgrade drop order wrong: {dropped}"

    # downgrade 也必须 drop 所有索引（7 个）
    dropped_idx = captured["drop_index"]
    assert len(dropped_idx) == 7, f"Expected 7 dropped indexes, got {len(dropped_idx)}"


def test_0007_upgrade_downgrade_round_trip() -> None:
    """升级 → 降级 → 升级 二次执行（alembic 不会二次跑，但函数可重复调用是基本盘）。"""
    module, captured = _load_0007_with_mocked_op()
    # upgrade → downgrade → upgrade 三轮；每轮 op.* 调用计数应正确
    _reset_op_capture(captured)
    module.upgrade()
    assert len(captured["create_table"]) == 4
    module.downgrade()
    assert len(captured["drop_table"]) == 4
    module.upgrade()
    assert len(captured["create_table"]) == 8  # 上一轮的 4 + 本轮 4


__all__ = [
    "test_0007_revision_metadata",
    "test_0007_creates_four_v2_tables",
    "test_0007_creates_seven_indexes",
    "test_0007_user_badges_unique_constraint",
    "test_0007_user_notification_prefs_composite_pk",
    "test_0007_account_deletion_check_constraint",
    "test_0007_user_self_tags_unique_and_check",
    "test_0007_downgrade_drops_all_four_tables_in_reverse",
    "test_0007_upgrade_downgrade_round_trip",
]