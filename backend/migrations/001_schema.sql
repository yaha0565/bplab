-- BPLab Trace LIMS V11 — PostgreSQL Schema

-- ============================================================
-- 用户与鉴权
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    username       TEXT PRIMARY KEY,
    display_name   TEXT NOT NULL,
    password_hash  TEXT NOT NULL,
    role           TEXT NOT NULL CHECK (role IN ('管理员','样品管理员','实验员','复核员','质量负责人')),
    enabled        BOOLEAN NOT NULL DEFAULT TRUE,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS sessions (
    token            TEXT PRIMARY KEY,
    username         TEXT NOT NULL REFERENCES users(username),
    expires_at       TIMESTAMPTZ NOT NULL,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_activity_at TIMESTAMPTZ
);

-- ============================================================
-- 单位 / 组织
-- ============================================================
CREATE TABLE IF NOT EXISTS organizations (
    id                     SERIAL PRIMARY KEY,
    org_code               TEXT UNIQUE,
    org_name               TEXT NOT NULL UNIQUE,
    short_name             TEXT,
    is_client              BOOLEAN DEFAULT FALSE,
    is_manufacturer        BOOLEAN DEFAULT FALSE,
    is_contract_manufacturer BOOLEAN DEFAULT FALSE,
    address                TEXT,
    contact                TEXT,
    phone                  TEXT,
    credit_code            TEXT,
    notes                  TEXT,
    enabled                BOOLEAN DEFAULT TRUE,
    created_at             TIMESTAMPTZ DEFAULT now(),
    updated_at             TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- 检测项目与方法
-- ============================================================
CREATE TABLE IF NOT EXISTS experiment_methods (
    experiment_code TEXT PRIMARY KEY,
    experiment_name TEXT NOT NULL UNIQUE,
    method_code     TEXT NOT NULL,
    standard        TEXT,
    category        TEXT,
    kind            TEXT,
    enabled         BOOLEAN DEFAULT TRUE,
    sort_order      INT DEFAULT 0,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- 样品目录
-- ============================================================
CREATE TABLE IF NOT EXISTS sample_catalog (
    id              SERIAL PRIMARY KEY,
    sample_code     TEXT UNIQUE,
    sample_name     TEXT NOT NULL,
    model           TEXT NOT NULL,
    material_name   TEXT NOT NULL,
    process         TEXT,
    material_suffix TEXT,
    source_sequence TEXT,
    category        TEXT,
    unit            TEXT DEFAULT '件',
    experiment_codes JSONB DEFAULT '[]',
    notes           TEXT,
    enabled         BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- 设备
-- ============================================================
CREATE TABLE IF NOT EXISTS equipment_registry (
    management_no      TEXT PRIMARY KEY,
    seq                INT,
    equipment_name     TEXT NOT NULL,
    model              TEXT,
    measuring_range    TEXT,
    manufacturer       TEXT,
    serial_no          TEXT,
    purchase_time      TEXT,
    calibration_time   TEXT,
    responsible        TEXT,
    equipment_class    TEXT,
    enabled            BOOLEAN DEFAULT TRUE,
    lifecycle_status   TEXT DEFAULT '启用',
    status_note        TEXT,
    notes              TEXT,
    created_at         TIMESTAMPTZ DEFAULT now(),
    updated_at         TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS device_presets (
    experiment             TEXT PRIMARY KEY,
    equipment_name         TEXT,
    equipment_model        TEXT,
    equipment_no           TEXT,
    calibration_certificate TEXT,
    calibration_due        TEXT,
    software               TEXT,
    default_location       TEXT,
    extra_json             JSONB DEFAULT '{}',
    updated_by             TEXT,
    updated_at             TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS experiment_equipment_bindings (
    experiment    TEXT NOT NULL,
    management_no TEXT NOT NULL REFERENCES equipment_registry(management_no),
    binding_role  TEXT NOT NULL,
    required      BOOLEAN DEFAULT FALSE,
    sort_order    INT DEFAULT 0,
    note          TEXT,
    created_at    TIMESTAMPTZ DEFAULT now(),
    updated_at    TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (experiment, management_no)
);

-- ============================================================
-- 实验配置版本
-- ============================================================
CREATE TABLE IF NOT EXISTS experiment_config_versions (
    id                  SERIAL PRIMARY KEY,
    experiment_code     TEXT NOT NULL,
    version             TEXT NOT NULL,
    experiment_name     TEXT NOT NULL,
    method_code         TEXT NOT NULL,
    standard            TEXT,
    category            TEXT,
    kind                TEXT DEFAULT 'generic',
    default_location    TEXT,
    sop_version         TEXT,
    record_template_version TEXT,
    software            TEXT,
    status              TEXT DEFAULT '草稿' CHECK (status IN ('草稿','现行','历史')),
    effective_date      DATE,
    note                TEXT,
    created_by          TEXT,
    created_at          TIMESTAMPTZ DEFAULT now(),
    approved_by         TEXT,
    approved_at         TIMESTAMPTZ,
    UNIQUE (experiment_code, version)
);

CREATE TABLE IF NOT EXISTS experiment_config_equipment (
    config_id     INT NOT NULL REFERENCES experiment_config_versions(id) ON DELETE CASCADE,
    management_no TEXT NOT NULL,
    binding_role  TEXT NOT NULL,
    required      BOOLEAN DEFAULT FALSE,
    sort_order    INT DEFAULT 0,
    note          TEXT,
    created_at    TIMESTAMPTZ DEFAULT now(),
    updated_at    TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (config_id, management_no)
);

CREATE TABLE IF NOT EXISTS experiment_config_fields (
    id             SERIAL PRIMARY KEY,
    config_id      INT NOT NULL REFERENCES experiment_config_versions(id) ON DELETE CASCADE,
    section_title  TEXT NOT NULL DEFAULT '',
    section_order  INT NOT NULL DEFAULT 1,
    field_key      TEXT NOT NULL,
    field_label    TEXT NOT NULL,
    field_type     TEXT NOT NULL DEFAULT 'text',
    field_default  TEXT DEFAULT '',
    field_options  TEXT DEFAULT '',
    is_required    BOOLEAN DEFAULT FALSE,
    is_readonly    BOOLEAN DEFAULT FALSE,
    is_actual      BOOLEAN DEFAULT FALSE,
    sort_order     INT DEFAULT 0
);

CREATE TABLE IF NOT EXISTS experiment_config_columns (
    id              SERIAL PRIMARY KEY,
    config_id       INT NOT NULL REFERENCES experiment_config_versions(id) ON DELETE CASCADE,
    column_key      TEXT NOT NULL,
    column_label    TEXT NOT NULL,
    column_type     TEXT NOT NULL DEFAULT 'number',
    is_required     BOOLEAN DEFAULT FALSE,
    column_default  TEXT,
    calc_expression TEXT,
    calc_precision  INT DEFAULT 3,
    sort_order      INT DEFAULT 0
);

CREATE TABLE IF NOT EXISTS experiment_config_photo_checkpoints (
    id               SERIAL PRIMARY KEY,
    config_id        INT NOT NULL REFERENCES experiment_config_versions(id) ON DELETE CASCADE,
    checkpoint_code  TEXT NOT NULL,
    checkpoint_label TEXT NOT NULL,
    is_required      BOOLEAN DEFAULT TRUE,
    is_sample_level  BOOLEAN DEFAULT FALSE,
    checkpoint_group TEXT,
    sort_order       INT DEFAULT 0
);

CREATE TABLE IF NOT EXISTS experiment_config_prechecks (
    id              SERIAL PRIMARY KEY,
    config_id       INT NOT NULL REFERENCES experiment_config_versions(id) ON DELETE CASCADE,
    precheck_code   TEXT NOT NULL,
    precheck_label  TEXT NOT NULL,
    is_required     BOOLEAN DEFAULT TRUE,
    sort_order      INT DEFAULT 0
);

CREATE TABLE IF NOT EXISTS experiment_config_validation_rules (
    id            SERIAL PRIMARY KEY,
    config_id     INT NOT NULL REFERENCES experiment_config_versions(id) ON DELETE CASCADE,
    rule_type     TEXT NOT NULL,
    target_field  TEXT NOT NULL,
    rule_value    TEXT NOT NULL,
    error_message TEXT,
    is_row_level  BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS template_field_mappings (
    id                  SERIAL PRIMARY KEY,
    config_id           INT NOT NULL REFERENCES experiment_config_versions(id) ON DELETE CASCADE,
    field_source        TEXT NOT NULL DEFAULT 'params',
    field_key           TEXT NOT NULL,
    template_name       TEXT NOT NULL,
    table_index         INT NOT NULL,
    row_index           INT NOT NULL,
    col_index           INT NOT NULL,
    transform           TEXT NOT NULL DEFAULT 'text',
    checkbox_selection  TEXT DEFAULT '',
    sort_order          INT DEFAULT 0,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS task_config_snapshots (
    task_no       TEXT PRIMARY KEY,
    config_id     INT,
    config_version TEXT,
    snapshot_json JSONB NOT NULL,
    snapshot_hash TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- 委托单 / 样品 / 检测项目
-- ============================================================
CREATE TABLE IF NOT EXISTS commissions (
    commission_no        TEXT PRIMARY KEY,
    client_org_id        INT NOT NULL,
    client_name          TEXT NOT NULL,
    client_address       TEXT,
    contact              TEXT,
    phone                TEXT,
    production_org_id    INT NOT NULL,
    production_org_name  TEXT NOT NULL,
    production_relation  TEXT NOT NULL,
    commission_date      DATE,
    due_date             DATE,
    subcontract_allowed  TEXT,
    report_medium        TEXT,
    conformity_judgment  TEXT,
    uncertainty          TEXT,
    delivery_method      TEXT,
    cnas_mark            TEXT,
    capability           TEXT,
    method_choices       JSONB DEFAULT '[]',
    notes                TEXT,
    status               TEXT DEFAULT '已入库',
    created_by           TEXT,
    created_at           TIMESTAMPTZ DEFAULT now(),
    updated_at           TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS sample_groups (
    id                    SERIAL PRIMARY KEY,
    group_no              TEXT NOT NULL UNIQUE,
    commission_no         TEXT NOT NULL REFERENCES commissions(commission_no),
    catalog_id            INT,
    sample_name           TEXT,
    model                 TEXT,
    material_name         TEXT,
    production_org_id     INT,
    production_org_name   TEXT,
    production_relation   TEXT,
    product_no            TEXT,
    production_date       TEXT,
    quantity              INT,
    unit                  TEXT,
    condition             TEXT,
    condition_note        TEXT,
    storage_area          TEXT,
    notes                 TEXT,
    status                TEXT DEFAULT '待分配',
    is_void               BOOLEAN DEFAULT FALSE,
    void_by               TEXT,
    void_at               TIMESTAMPTZ,
    void_reason           TEXT,
    created_at            TIMESTAMPTZ DEFAULT now(),
    updated_at            TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS samples (
    sample_no        TEXT PRIMARY KEY,
    group_id         INT NOT NULL REFERENCES sample_groups(id),
    group_no         TEXT NOT NULL,
    commission_no    TEXT NOT NULL,
    sample_name      TEXT,
    model            TEXT,
    material_name    TEXT,
    condition        TEXT,
    condition_note   TEXT,
    current_location TEXT,
    current_holder   TEXT,
    status           TEXT DEFAULT '待分配',
    created_at       TIMESTAMPTZ DEFAULT now(),
    updated_at       TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS requested_tests (
    id              SERIAL PRIMARY KEY,
    group_id        INT NOT NULL REFERENCES sample_groups(id),
    experiment_code TEXT NOT NULL,
    experiment      TEXT NOT NULL,
    method_code     TEXT NOT NULL,
    standard        TEXT,
    status          TEXT DEFAULT '待分配',
    task_no         TEXT,
    UNIQUE (group_id, experiment_code)
);

-- ============================================================
-- 任务包 / 任务 / 记录
-- ============================================================
CREATE TABLE IF NOT EXISTS task_packages (
    package_no         TEXT PRIMARY KEY,
    commission_no      TEXT NOT NULL,
    group_id           INT NOT NULL,
    group_no           TEXT NOT NULL,
    assignee           TEXT NOT NULL,
    reviewer           TEXT NOT NULL,
    quality_inspector  TEXT,
    material_name      TEXT,
    sample_nos         TEXT,
    experiment_codes   TEXT,
    experiments        TEXT,
    status             TEXT DEFAULT '待接收',
    assigned_by        TEXT,
    assigned_at        TIMESTAMPTZ DEFAULT now(),
    notified_at        TIMESTAMPTZ,
    accepted_at        TIMESTAMPTZ,
    detection_location TEXT,
    acceptance_result  TEXT,
    acceptance_note    TEXT,
    return_submitted_at TIMESTAMPTZ,
    return_confirmed_at TIMESTAMPTZ,
    created_at         TIMESTAMPTZ DEFAULT now(),
    updated_at         TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS tasks (
    task_no              TEXT PRIMARY KEY,
    package_no           TEXT NOT NULL REFERENCES task_packages(package_no),
    commission_no        TEXT NOT NULL,
    group_id             INT NOT NULL,
    group_no             TEXT NOT NULL,
    sample_nos           TEXT,
    experiment_code      TEXT NOT NULL,
    experiment           TEXT,
    method_code          TEXT,
    standard             TEXT,
    material_name        TEXT,
    assignee             TEXT,
    reviewer             TEXT,
    quality_inspector    TEXT,
    status               TEXT DEFAULT '待接收',
    detection_location   TEXT,
    experiment_started_at TIMESTAMPTZ,
    experiment_ended_at   TIMESTAMPTZ,
    created_at           TIMESTAMPTZ DEFAULT now(),
    updated_at           TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS records (
    id                  SERIAL PRIMARY KEY,
    record_no           TEXT NOT NULL,
    task_no             TEXT NOT NULL,
    version             INT NOT NULL,
    experiment          TEXT,
    owner               TEXT,
    status              TEXT,
    payload             JSONB,
    template_version    TEXT,
    sop_version         TEXT,
    change_reason       TEXT,
    tester_signed_at    TIMESTAMPTZ,
    reviewer_signed_at  TIMESTAMPTZ,
    quality_signed_at   TIMESTAMPTZ,
    created_at          TIMESTAMPTZ DEFAULT now(),
    updated_at          TIMESTAMPTZ DEFAULT now(),
    UNIQUE (record_no, version)
);

CREATE TABLE IF NOT EXISTS reviews (
    id               SERIAL PRIMARY KEY,
    record_no        TEXT,
    version          INT,
    reviewer         TEXT,
    decision         TEXT,
    comment          TEXT,
    correction_fields JSONB DEFAULT '[]',
    reviewed_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS package_loans (
    id                  SERIAL PRIMARY KEY,
    package_no          TEXT NOT NULL,
    sample_no           TEXT NOT NULL,
    borrower            TEXT,
    borrowed_at         TIMESTAMPTZ DEFAULT now(),
    purpose             TEXT,
    detection_location  TEXT,
    issue_note          TEXT,
    return_condition    TEXT,
    return_note         TEXT,
    returned_by         TEXT,
    returned_at         TIMESTAMPTZ,
    return_status       TEXT DEFAULT '未归还',
    confirmed_by        TEXT,
    confirmed_at        TIMESTAMPTZ,
    confirmed_location  TEXT,
    UNIQUE (package_no, sample_no)
);

-- ============================================================
-- 报告
-- ============================================================
CREATE TABLE IF NOT EXISTS reports (
    report_no             TEXT PRIMARY KEY,
    commission_no         TEXT NOT NULL,
    task_no               TEXT UNIQUE,
    status                TEXT DEFAULT '草稿',
    tester                TEXT,
    verifier              TEXT,
    quality_inspector     TEXT,
    approver              TEXT,
    source_versions       TEXT,
    validity_status       TEXT DEFAULT '现行有效',
    supersedes_report_no  TEXT,
    report_category       TEXT DEFAULT '常规',
    sample_statement      TEXT,
    conclusion            TEXT,
    notes                 TEXT,
    signed_by_tester      TIMESTAMPTZ,
    signed_by_verifier    TIMESTAMPTZ,
    signed_by_quality     TIMESTAMPTZ,
    signed_by_approver    TIMESTAMPTZ,
    publish_date          DATE,
    created_at            TIMESTAMPTZ DEFAULT now(),
    updated_at            TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS report_actions (
    id         SERIAL PRIMARY KEY,
    report_no  TEXT NOT NULL REFERENCES reports(report_no),
    actor      TEXT,
    action     TEXT,
    comment    TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS report_deliveries (
    id                SERIAL PRIMARY KEY,
    report_no         TEXT NOT NULL,
    client_name       TEXT,
    delivery_method   TEXT,
    recipient         TEXT,
    recipient_contact TEXT,
    delivered_at      TIMESTAMPTZ DEFAULT now(),
    receipt_status    TEXT,
    receipt_note      TEXT,
    created_at        TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- 附件
-- ============================================================
CREATE TABLE IF NOT EXISTS attachments (
    id                  SERIAL PRIMARY KEY,
    attachment_id       TEXT UNIQUE,
    commission_no       TEXT,
    package_no          TEXT,
    task_no             TEXT,
    sample_no           TEXT,
    attachment_type     TEXT,
    original_name       TEXT,
    stored_name         TEXT,
    relative_path       TEXT,
    sha256              TEXT,
    captured_at         TIMESTAMPTZ,
    uploader            TEXT,
    description         TEXT,
    is_original         BOOLEAN DEFAULT TRUE,
    parent_attachment_id TEXT,
    capture_source      TEXT DEFAULT 'file',
    checkpoint_code     TEXT,
    checkpoint_label    TEXT,
    device_id           TEXT,
    evidence_status     TEXT DEFAULT '有效',
    server_captured_at  TIMESTAMPTZ DEFAULT now(),
    created_at          TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- 审计 / 日志
-- ============================================================
CREATE TABLE IF NOT EXISTS audit_logs (
    id             SERIAL PRIMARY KEY,
    entity_type    TEXT,
    entity_id      TEXT,
    actor          TEXT,
    actor_name     TEXT,
    actor_role     TEXT,
    action         TEXT,
    field_name     TEXT,
    old_value      TEXT,
    new_value      TEXT,
    reason         TEXT,
    client_time    TEXT,
    device_id      TEXT,
    session_token  TEXT,
    snapshot_hash  TEXT,
    previous_hash  TEXT,
    entry_hash     TEXT,
    created_at     TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS sample_events (
    id            SERIAL PRIMARY KEY,
    sample_no     TEXT,
    actor         TEXT,
    action        TEXT,
    from_status   TEXT,
    to_status     TEXT,
    from_location TEXT,
    to_location   TEXT,
    details       TEXT,
    created_at    TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS document_versions (
    id            SERIAL PRIMARY KEY,
    entity_type   TEXT,
    entity_id     TEXT,
    version       INT,
    status        TEXT,
    snapshot_json JSONB,
    snapshot_hash TEXT,
    created_by    TEXT,
    created_at    TIMESTAMPTZ DEFAULT now(),
    obsolete_by   TEXT,
    obsolete_at   TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS modification_logs (
    id            SERIAL PRIMARY KEY,
    entity_type   TEXT,
    entity_id     TEXT,
    actor         TEXT,
    action        TEXT,
    field_name    TEXT,
    old_value     TEXT,
    new_value     TEXT,
    reason        TEXT,
    created_at    TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- 客户异议 / 设备故障 / 危废 / 其他
-- ============================================================
CREATE TABLE IF NOT EXISTS objections (
    objection_no               TEXT PRIMARY KEY,
    report_no                  TEXT,
    commission_no              TEXT,
    client_name                TEXT,
    contact                    TEXT,
    description                TEXT,
    evidence_note              TEXT,
    status                     TEXT DEFAULT '待处理',
    pathway                    TEXT,
    investigation              TEXT,
    trace_conclusion           TEXT,
    quality_conclusion         TEXT,
    quality_comment            TEXT,
    response_body              TEXT,
    admin_decision             TEXT,
    customer_retest_decision   TEXT,
    retest_task_no             TEXT,
    final_conclusion           TEXT,
    response_sent_at           TIMESTAMPTZ,
    archived_at                TIMESTAMPTZ,
    created_at                 TIMESTAMPTZ DEFAULT now(),
    updated_at                 TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS objection_actions (
    id           SERIAL PRIMARY KEY,
    objection_no TEXT NOT NULL,
    actor        TEXT,
    action       TEXT,
    comment      TEXT,
    created_at   TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS equipment_incidents (
    incident_no        TEXT PRIMARY KEY,
    task_no            TEXT,
    equipment_no       TEXT,
    fault_type         TEXT,
    fault_description  TEXT,
    status             TEXT DEFAULT '报告',
    quality_conclusion TEXT,
    impact_scope       TEXT,
    recovery_route     TEXT,
    created_by         TEXT,
    created_at         TIMESTAMPTZ DEFAULT now(),
    updated_at         TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS equipment_incident_actions (
    id          SERIAL PRIMARY KEY,
    incident_no TEXT NOT NULL,
    actor       TEXT,
    action      TEXT,
    comment     TEXT,
    created_at  TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS hazardous_waste_records (
    disposal_no    TEXT PRIMARY KEY,
    commission_no  TEXT,
    task_no        TEXT,
    task_nos       JSONB DEFAULT '[]',
    sample_no      TEXT,
    waste_type     TEXT,
    waste_name     TEXT,
    quantity       REAL,
    unit           TEXT,
    hazard_category TEXT,
    disposal_method TEXT,
    container_no   TEXT,
    handler        TEXT,
    occurred_at    TIMESTAMPTZ DEFAULT now(),
    status         TEXT DEFAULT '已登记',
    created_at     TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- 签名 / 模板 / 通知 / 草稿
-- ============================================================
CREATE TABLE IF NOT EXISTS signatures (
    username     TEXT PRIMARY KEY,
    source_file  TEXT,
    image_file   TEXT,
    uploaded_by  TEXT,
    uploaded_at  TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS template_versions (
    experiment     TEXT NOT NULL,
    doc_type       TEXT NOT NULL CHECK (doc_type IN ('原始记录表','SOP')),
    file_name      TEXT NOT NULL,
    version        TEXT NOT NULL DEFAULT 'A/0',
    effective_date DATE,
    status         TEXT DEFAULT '现行',
    created_at     TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (experiment, doc_type, version)
);

CREATE TABLE IF NOT EXISTS notifications (
    id          SERIAL PRIMARY KEY,
    recipient   TEXT NOT NULL,
    title       TEXT,
    message     TEXT,
    entity_type TEXT,
    entity_id   TEXT,
    read_at     TIMESTAMPTZ,
    created_at  TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS form_drafts (
    session_token TEXT NOT NULL,
    page          TEXT NOT NULL,
    draft_key     TEXT NOT NULL,
    payload       JSONB,
    created_at    TIMESTAMPTZ DEFAULT now(),
    updated_at    TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (session_token, page, draft_key)
);

-- ============================================================
-- 索引
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_sessions_username ON sessions(username);
CREATE INDEX IF NOT EXISTS idx_commissions_status ON commissions(status);
CREATE INDEX IF NOT EXISTS idx_sample_groups_commission ON sample_groups(commission_no);
CREATE INDEX IF NOT EXISTS idx_samples_group ON samples(group_id);
CREATE INDEX IF NOT EXISTS idx_task_packages_assignee ON task_packages(assignee);
CREATE INDEX IF NOT EXISTS idx_task_packages_status ON task_packages(status);
CREATE INDEX IF NOT EXISTS idx_tasks_package ON tasks(package_no);
CREATE INDEX IF NOT EXISTS idx_tasks_assignee ON tasks(assignee);
CREATE INDEX IF NOT EXISTS idx_records_task ON records(task_no);
CREATE INDEX IF NOT EXISTS idx_records_status ON records(status);
CREATE INDEX IF NOT EXISTS idx_reports_commission ON reports(commission_no);
CREATE INDEX IF NOT EXISTS idx_reports_status ON reports(status);
CREATE INDEX IF NOT EXISTS idx_attachments_task ON attachments(task_no);
CREATE INDEX IF NOT EXISTS idx_audit_logs_entity ON audit_logs(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_notifications_recipient ON notifications(recipient, read_at);
CREATE INDEX IF NOT EXISTS idx_package_loans_package ON package_loans(package_no);
CREATE INDEX IF NOT EXISTS idx_experiment_config_status ON experiment_config_versions(status);
CREATE INDEX IF NOT EXISTS idx_objections_report ON objections(report_no);
CREATE INDEX IF NOT EXISTS idx_equipment_incidents_status ON equipment_incidents(status);
