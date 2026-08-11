"""SQLite → PostgreSQL 数据迁移 (遗留工具，仅用于从旧版 SQLite 迁移)
用法: python -m migrations.002_migrate  (from backend/ 目录)

注意：当前系统已完全使用 PostgreSQL，此脚本仅保留作为历史参考。
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import psycopg2
from psycopg2.extras import execute_values
import bcrypt

# ── 路径 ──
ROOT = Path(__file__).parent.parent.parent
SQLITE_PATH = ROOT / "data" / "bplab_trace_v56.db"

# ── PostgreSQL 连接 ──
PG_DSN = "host=localhost port=5432 dbname=bplab user=postgres password=123456"


def _bcrypt_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


# 已知演示用户密码
DEMO_CREDENTIALS = {
    "admin": "admin123",
    "receiver": "receive123",
    "liuhong_test": "LhTest2026",
    "liuhong_review": "LhReview2026",
    "lihongli_test": "LhlTest2026",
    "lihongli_review": "LhlReview2026",
    "quality": "quality123",
}

# ── 表迁移顺序（按外键依赖排序，父表在前） ──
MIGRATION_TABLES: list[tuple[str, str, set[str], set[str]]] = [
    # 基础表（无 FK）
    ("users", "users", {"enabled"}, set()),
    ("organizations", "organizations", {"is_client", "is_manufacturer", "is_contract_manufacturer", "enabled"}, set()),
    ("experiment_methods", "experiment_methods", {"enabled"}, set()),
    ("sample_catalog", "sample_catalog", {"enabled"}, set()),
    ("equipment_registry", "equipment_registry", {"enabled"}, set()),
    ("device_presets", "device_presets", set(), set()),
    ("signatures", "signatures", set(), set()),
    # 设备绑定
    ("experiment_equipment_bindings", "experiment_equipment_bindings", {"required"}, set()),
    # 实验配置版本（父表）
    ("experiment_config_versions", "experiment_config_versions", set(), set()),
    # 实验配置子表
    ("experiment_config_equipment", "experiment_config_equipment", {"required"}, set()),
    # 以下表在 SQLite 中可能不存在
    ("experiment_config_fields", "experiment_config_fields", {"is_required", "is_readonly", "is_actual"}, set()),
    ("experiment_config_columns", "experiment_config_columns", {"is_required"}, set()),
    ("experiment_config_photo_checkpoints", "experiment_config_photo_checkpoints", {"is_required", "is_sample_level"}, set()),
    ("experiment_config_prechecks", "experiment_config_prechecks", {"is_required"}, set()),
    ("experiment_config_validation_rules", "experiment_config_validation_rules", {"is_row_level"}, set()),
    ("template_field_mappings", "template_field_mappings", set(), set()),
    # template_versions: SQLite 有 id 列，PG 用复合主键
    ("template_versions", "template_versions", set(), {"id"}),
    # 业务表
    ("commissions", "commissions", set(), set()),
    ("sample_groups", "sample_groups", {"is_void"}, set()),
    ("samples", "samples", set(), set()),
    ("requested_tests", "requested_tests", set(), set()),
    ("task_packages", "task_packages", set(), set()),
    ("tasks", "tasks", set(), set()),
    ("records", "records", set(), set()),
    ("reviews", "reviews", set(), set()),
    ("package_loans", "package_loans", set(), set()),
    ("reports", "reports", set(), set()),
    ("report_actions", "report_actions", set(), set()),
    ("report_deliveries", "report_deliveries", set(), set()),
    ("attachments", "attachments", {"is_original"}, set()),
    ("audit_logs", "audit_logs", set(), set()),
    ("sample_events", "sample_events", set(), set()),
    ("document_versions", "document_versions", set(), set()),
    ("modification_logs", "modification_logs", set(), set()),
    ("objections", "objections", set(), set()),
    ("objection_actions", "objection_actions", set(), set()),
    ("equipment_incidents", "equipment_incidents", set(), set()),
    ("equipment_incident_actions", "equipment_incident_actions", set(), set()),
    ("hazardous_waste_records", "hazardous_waste_records", set(), set()),
    ("notifications", "notifications", set(), set()),
    ("form_drafts", "form_drafts", set(), set()),
    ("task_config_snapshots", "task_config_snapshots", set(), set()),
]


def convert_row(row: tuple, cols: list[str], bool_cols: set[str]) -> tuple:
    """将 SQLite row 转为 PG 兼容值"""
    result = []
    for i, val in enumerate(row):
        col = cols[i] if i < len(cols) else ""
        if val is None:
            result.append(None)
        elif col in bool_cols:
            result.append(bool(val))
        elif col in ("payload", "snapshot_json", "experiment_codes",
                     "method_choices", "correction_fields", "extra_json",
                     "task_nos") and isinstance(val, str):
            try:
                result.append(json.dumps(json.loads(val)))
            except (json.JSONDecodeError, TypeError):
                result.append(val)
        else:
            result.append(val)
    return tuple(result)


def migrate():
    print("=" * 60)
    print("BPLab Trace - SQLite -> PostgreSQL Data Migration")
    print("=" * 60)

    # ── 1. 连接 SQLite ──
    if not SQLITE_PATH.exists():
        print(f"\nERROR: SQLite database not found: {SQLITE_PATH}")
        sys.exit(1)
    sq = sqlite3.connect(str(SQLITE_PATH))
    sq.row_factory = sqlite3.Row
    print(f"\nSQLite: {SQLITE_PATH}  ({SQLITE_PATH.stat().st_size / 1024 / 1024:.1f} MB)")

    # ── 2. 连接 PostgreSQL ──
    try:
        pg = psycopg2.connect(PG_DSN)
        pg.autocommit = True
        print("PostgreSQL: connected")
    except psycopg2.OperationalError as e:
        print(f"\nERROR: PostgreSQL connection failed: {e}")
        sys.exit(1)

    # ── 3. 清空所有表 ──
    print("\nClearing existing data...")
    cur = pg.cursor()
    cur.execute("""
        DO $$ DECLARE r RECORD;
        BEGIN
            FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname='public') LOOP
                EXECUTE 'TRUNCATE TABLE ' || quote_ident(r.tablename) || ' CASCADE';
            END LOOP;
        END $$;
    """)
    cur.close()
    print("All tables truncated")

    # ── 4. 获取 PG 表实际列名 ──
    cur = pg.cursor()
    pg_cols_cache: dict[str, list[str]] = {}
    for _, pg_table, _, _ in MIGRATION_TABLES:
        cur.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_schema='public' AND table_name=%s
            ORDER BY ordinal_position
        """, (pg_table,))
        pg_cols_cache[pg_table] = [r[0] for r in cur.fetchall()]
    cur.close()

    # ── 5. 迁移数据 ──
    for sqlite_table, pg_table, bool_cols, skip_cols in MIGRATION_TABLES:
        print(f"  -> {pg_table}...", end=" ")

        # 检查 SQLite 表是否存在
        try:
            rows = sq.execute(f"SELECT * FROM {sqlite_table}").fetchall()
        except sqlite3.OperationalError:
            print("SQLite table not found, skip")
            continue

        if not rows:
            print("empty, skip")
            continue

        sqlite_cols = [desc[0] for desc in sq.execute(
            f"SELECT * FROM {sqlite_table} LIMIT 0").description]

        # 构建插入列（排除 skip_cols）
        insert_cols = [c for c in sqlite_cols if c not in skip_cols]
        pg_cols = pg_cols_cache.get(pg_table, insert_cols)

        # 只插入 PG 表中存在的列
        final_cols = [c for c in insert_cols if c in pg_cols]

        # 转换数据
        converted = []
        for row in rows:
            row_dict = dict(zip(sqlite_cols, tuple(row)))
            filtered_vals = [row_dict[c] for c in final_cols]
            conv = convert_row(tuple(filtered_vals), final_cols, bool_cols)
            converted.append(conv)

        # 特殊处理 users 表 - bcrypt 密码
        if sqlite_table == "users":
            new_rows = []
            pwd_idx = final_cols.index("password_hash")
            for i, row in enumerate(rows):
                username = dict(row)["username"]
                if username in DEMO_CREDENTIALS:
                    new_hash = _bcrypt_hash(DEMO_CREDENTIALS[username])
                else:
                    new_hash = _bcrypt_hash("changeme123")
                conv = list(converted[i])
                conv[pwd_idx] = new_hash
                new_rows.append(tuple(conv))
            converted = new_rows

        col_names = ", ".join(f'"{c}"' for c in final_cols)
        sql = f'INSERT INTO {pg_table} ({col_names}) VALUES %s ON CONFLICT DO NOTHING'

        cur = pg.cursor()
        try:
            execute_values(cur, sql, converted, template=None, page_size=200)
            print(f"{len(converted)} rows")
        except Exception as e:
            print(f"ERROR: {e}")
            pg.rollback()
        finally:
            cur.close()

    # ── 6. 更新序列 ──
    print("\nUpdating sequences...")
    cur = pg.cursor()
    cur.execute("""
        SELECT table_name, column_name
        FROM information_schema.columns
        WHERE table_schema='public'
          AND column_default LIKE 'nextval%'
        ORDER BY table_name
    """)
    serial_cols = cur.fetchall()

    for table_name, col_name in serial_cols:
        seq_name = f"{table_name}_{col_name}_seq"
        cur.execute(
            f"SELECT setval(%s, COALESCE((SELECT MAX({col_name}) FROM {table_name}), 1), "
            f"(SELECT MAX({col_name}) FROM {table_name}) IS NOT NULL)",
            (seq_name,)
        )
    cur.close()
    print(f"  {len(serial_cols)} sequences updated")

    # ── 7. 验证 ──
    print("\nMigration summary:")
    cur = pg.cursor()
    for _, pg_table, _, _ in MIGRATION_TABLES:
        try:
            cur.execute(f"SELECT COUNT(*) FROM {pg_table}")
            count = cur.fetchone()[0]
            if count > 0:
                print(f"  {pg_table}: {count} rows")
        except Exception:
            pass
    cur.close()

    sq.close()
    pg.close()
    print("\n[DONE] Migration completed!")


if __name__ == "__main__":
    migrate()
