-- Phase 4: 对齐参考项目 bp-lims V9.4.2 — 扩展业务表字段
-- 执行方式: psql -U <user> -d <db> -f migrations/002_phase4_columns.sql

-- ============================================================
-- 1. equipment_incidents — 设备故障处置完整字段
-- ============================================================
ALTER TABLE equipment_incidents ADD COLUMN IF NOT EXISTS package_no TEXT;
ALTER TABLE equipment_incidents ADD COLUMN IF NOT EXISTS group_id INTEGER;
ALTER TABLE equipment_incidents ADD COLUMN IF NOT EXISTS equipment_name TEXT;
ALTER TABLE equipment_incidents ADD COLUMN IF NOT EXISTS reporter TEXT;
ALTER TABLE equipment_incidents ADD COLUMN IF NOT EXISTS occurred_at TIMESTAMPTZ;
ALTER TABLE equipment_incidents ADD COLUMN IF NOT EXISTS error_code TEXT;
ALTER TABLE equipment_incidents ADD COLUMN IF NOT EXISTS current_stage TEXT;
ALTER TABLE equipment_incidents ADD COLUMN IF NOT EXISTS completed_steps TEXT;
ALTER TABLE equipment_incidents ADD COLUMN IF NOT EXISTS collected_data TEXT;
ALTER TABLE equipment_incidents ADD COLUMN IF NOT EXISTS sample_condition TEXT;
ALTER TABLE equipment_incidents ADD COLUMN IF NOT EXISTS risk_types JSONB DEFAULT '[]';
ALTER TABLE equipment_incidents ADD COLUMN IF NOT EXISTS immediate_actions JSONB DEFAULT '[]';
ALTER TABLE equipment_incidents ADD COLUMN IF NOT EXISTS involved_samples JSONB DEFAULT '[]';
ALTER TABLE equipment_incidents ADD COLUMN IF NOT EXISTS frozen_record_version INTEGER;
ALTER TABLE equipment_incidents ADD COLUMN IF NOT EXISTS isolation_location TEXT;
ALTER TABLE equipment_incidents ADD COLUMN IF NOT EXISTS storage_requirements TEXT;
ALTER TABLE equipment_incidents ADD COLUMN IF NOT EXISTS sample_validity TEXT;
ALTER TABLE equipment_incidents ADD COLUMN IF NOT EXISTS receiver_note TEXT;
ALTER TABLE equipment_incidents ADD COLUMN IF NOT EXISTS receiver_by TEXT;
ALTER TABLE equipment_incidents ADD COLUMN IF NOT EXISTS receiver_at TIMESTAMPTZ;
ALTER TABLE equipment_incidents ADD COLUMN IF NOT EXISTS quality_note TEXT;
ALTER TABLE equipment_incidents ADD COLUMN IF NOT EXISTS quality_by TEXT;
ALTER TABLE equipment_incidents ADD COLUMN IF NOT EXISTS quality_at TIMESTAMPTZ;
ALTER TABLE equipment_incidents ADD COLUMN IF NOT EXISTS backup_equipment_no TEXT;
ALTER TABLE equipment_incidents ADD COLUMN IF NOT EXISTS performance_check_result TEXT;
ALTER TABLE equipment_incidents ADD COLUMN IF NOT EXISTS admin_note TEXT;
ALTER TABLE equipment_incidents ADD COLUMN IF NOT EXISTS approved_by TEXT;
ALTER TABLE equipment_incidents ADD COLUMN IF NOT EXISTS approved_at TIMESTAMPTZ;
ALTER TABLE equipment_incidents ADD COLUMN IF NOT EXISTS resumed_record_version INTEGER;
ALTER TABLE equipment_incidents ADD COLUMN IF NOT EXISTS closed_at TIMESTAMPTZ;

-- ============================================================
-- 2. objections — 客户异议完整字段
-- ============================================================
ALTER TABLE objections ADD COLUMN IF NOT EXISTS submitted_at TIMESTAMPTZ;
ALTER TABLE objections ADD COLUMN IF NOT EXISTS quality_inspector TEXT;
ALTER TABLE objections ADD COLUMN IF NOT EXISTS disputed_items TEXT;
ALTER TABLE objections ADD COLUMN IF NOT EXISTS involved_samples TEXT;
ALTER TABLE objections ADD COLUMN IF NOT EXISTS application_channel TEXT;
ALTER TABLE objections ADD COLUMN IF NOT EXISTS quality_evidence TEXT;
ALTER TABLE objections ADD COLUMN IF NOT EXISTS quality_method_check TEXT;
ALTER TABLE objections ADD COLUMN IF NOT EXISTS quality_equipment_check TEXT;
ALTER TABLE objections ADD COLUMN IF NOT EXISTS quality_environment_check TEXT;
ALTER TABLE objections ADD COLUMN IF NOT EXISTS quality_operation_check TEXT;
ALTER TABLE objections ADD COLUMN IF NOT EXISTS quality_calculation_check TEXT;
ALTER TABLE objections ADD COLUMN IF NOT EXISTS impact_scope TEXT;
ALTER TABLE objections ADD COLUMN IF NOT EXISTS treatment_suggestion TEXT;
ALTER TABLE objections ADD COLUMN IF NOT EXISTS retest_note TEXT;
ALTER TABLE objections ADD COLUMN IF NOT EXISTS customer_contact_at TIMESTAMPTZ;
ALTER TABLE objections ADD COLUMN IF NOT EXISTS customer_contact_method TEXT;
ALTER TABLE objections ADD COLUMN IF NOT EXISTS replacement_report_no TEXT;
ALTER TABLE objections ADD COLUMN IF NOT EXISTS response_text TEXT;
ALTER TABLE objections ADD COLUMN IF NOT EXISTS response_method TEXT;
ALTER TABLE objections ADD COLUMN IF NOT EXISTS response_receipt TEXT;
ALTER TABLE objections ADD COLUMN IF NOT EXISTS registered_by TEXT;
ALTER TABLE objections ADD COLUMN IF NOT EXISTS investigated_at TIMESTAMPTZ;
ALTER TABLE objections ADD COLUMN IF NOT EXISTS approved_by TEXT;
ALTER TABLE objections ADD COLUMN IF NOT EXISTS approved_at TIMESTAMPTZ;
ALTER TABLE objections ADD COLUMN IF NOT EXISTS sent_by TEXT;
ALTER TABLE objections ADD COLUMN IF NOT EXISTS sent_at TIMESTAMPTZ;

-- ============================================================
-- 3. tasks — 实验时间 + 检测地点
-- ============================================================
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS detection_location TEXT;
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS experiment_started_at TIMESTAMPTZ;
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS experiment_ended_at TIMESTAMPTZ;

-- ============================================================
-- 4. notifications — 字段对齐（001 已建表，用 message/read_at）
-- ============================================================
-- 确保 notifications 表有 message 和 read_at 列（如从旧版本迁移）
DO $$ BEGIN
  ALTER TABLE notifications ADD COLUMN IF NOT EXISTS message TEXT;
  ALTER TABLE notifications ADD COLUMN IF NOT EXISTS read_at TIMESTAMPTZ;
EXCEPTION WHEN duplicate_table THEN NULL;
END $$;

-- ============================================================
-- 5. signatures — 字段对齐
-- ============================================================
ALTER TABLE signatures ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT now();
ALTER TABLE signatures ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT now();

-- ============================================================
-- 6. hazardous_waste_records — 缺失字段
-- ============================================================
ALTER TABLE hazardous_waste_records ADD COLUMN IF NOT EXISTS note TEXT;
ALTER TABLE hazardous_waste_records ADD COLUMN IF NOT EXISTS created_by TEXT;
ALTER TABLE hazardous_waste_records ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT now();

-- ============================================================
-- 7. objections — 补充字段（超出 002 原有调整的新增字段）
-- ============================================================
ALTER TABLE objections ADD COLUMN IF NOT EXISTS retest_note TEXT;
ALTER TABLE objections ADD COLUMN IF NOT EXISTS registered_by TEXT;
ALTER TABLE objections ADD COLUMN IF NOT EXISTS investigated_at TIMESTAMPTZ;
ALTER TABLE objections ADD COLUMN IF NOT EXISTS approved_by TEXT;
ALTER TABLE objections ADD COLUMN IF NOT EXISTS approved_at TIMESTAMPTZ;
ALTER TABLE objections ADD COLUMN IF NOT EXISTS sent_by TEXT;
ALTER TABLE objections ADD COLUMN IF NOT EXISTS sent_at TIMESTAMPTZ;
ALTER TABLE objections ADD COLUMN IF NOT EXISTS archived_at TIMESTAMPTZ;
ALTER TABLE objections ADD COLUMN IF NOT EXISTS response_text TEXT;
ALTER TABLE objections ADD COLUMN IF NOT EXISTS response_method TEXT;
ALTER TABLE objections ADD COLUMN IF NOT EXISTS response_receipt TEXT;

-- ============================================================
-- 8. reports — 报告状态扩展
-- ============================================================
ALTER TABLE reports ADD COLUMN IF NOT EXISTS validity_status TEXT;  -- 有效/异议成立-暂停使用/异议处理中
