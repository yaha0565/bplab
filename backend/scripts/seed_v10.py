"""
V10.0 Seed Script - Import 14 experiment methods, 99 equipment, bindings, templates
Run once to upgrade from V9.x to V10.0
Usage: cd backend && python scripts/seed_v10.py
"""
from __future__ import annotations

import asyncio
import csv
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import async_session
from sqlalchemy import text

ROOT = Path(__file__).parent.parent.parent
ZIP_EXTRACT = ROOT / "资料" / "bplab_v10_update" / "bplab_v10_template_update"
EQUIPMENT_CSV = ZIP_EXTRACT / "equipment_master.csv"
BINDING_CSV = ZIP_EXTRACT / "equipment_binding_matrix.csv"
TEMPLATE_SRC = ZIP_EXTRACT / "templates"
TEMPLATE_DST = ROOT / "templates"

EXPERIMENT_METHODS = [
    ("I001", "表面粗糙度试验", "YY/T 1702", "YY/T 1702-2020", "roughness"),
    ("I002", "金属-陶瓷结合裂纹萌生试验", "YY 0621.1", "YY 0621.1-2016", "crack"),
    ("I003", "金属内部质量X射线灰度分析", "GB 17168", "GB 17168-2013", "xray"),
    ("I004", "翘曲变形试验", "YY/T 1702", "YY/T 1702-2020", "warpage"),
    ("I005", "热膨胀系数试验", "YY 0621.1", "YY 0621.1-2016", "cte"),
    ("I006", "陶瓷牙耐急冷急热试验", "YY 0300", "YY 0300-2009", "thermal_shock"),
    ("I007", "弯曲性能试验", "YY/T 1702", "YY/T 1702-2020", "bending"),
    ("I008", "维氏硬度试验", "GB/T 4340.1", "GB/T 4340.1-2024", "vickers"),
    ("I009", "增材制造金属试样厚度测量", "YY/T 1702", "YY/T 1702-2020", "thickness"),
    ("I010", "牙科材料色稳定性试验", "YY 0710", "YY 0710-2009", "color_stability"),
    ("I011", "定制式固定义齿检验", "GB 17168", "GB 17168-2013", "fixed_denture"),
    ("I012", "定制式活动义齿检验", "GB 17168", "GB 17168-2013", "removable_denture"),
    ("I013", "激光选区熔化金属材料密度试验", "YY/T 1702", "YY/T 1702-2020", "density"),
    ("I014", "金属材料抗晦暗性能试验", "YY 0710", "YY 0710-2009", "tarnish"),
]


async def seed_experiment_methods(db) -> int:
    count = 0
    for code, name, method, standard, kind in EXPERIMENT_METHODS:
        existing = await db.execute(
            text("SELECT 1 FROM experiment_methods WHERE experiment_code=:c"), {"c": code}
        )
        if existing.fetchone():
            await db.execute(
                text("""
                    UPDATE experiment_methods
                    SET experiment_name=:n, method_code=:m, standard=:s, kind=:k, updated_at=localtimestamp
                    WHERE experiment_code=:c
                """),
                {"n": name, "m": method, "s": standard, "k": kind, "c": code},
            )
            print(f"  Updated: {code} {name}")
        else:
            await db.execute(
                text("""
                    INSERT INTO experiment_methods (experiment_code, experiment_name, method_code, standard,
                        kind, enabled, created_at, updated_at)
                    VALUES (:c, :n, :m, :s, :k, TRUE, localtimestamp, localtimestamp)
                """),
                {"c": code, "n": name, "m": method, "s": standard, "k": kind},
            )
            print(f"  Inserted: {code} {name}")
            count += 1
    return count


async def seed_equipment(db) -> int:
    inserted, updated = 0, 0
    with open(EQUIPMENT_CSV, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    for row in rows:
        name = (row.get("名称") or "").strip()
        model = (row.get("规格型号") or "").strip()
        measuring_range = (row.get("测量范围") or "").strip()
        manufacturer = (row.get("生产厂家") or "").strip()
        serial_no = (row.get("出厂编号") or "").strip()
        mgmt_no = (row.get("管理编号") or "").strip()
        purchase_time = (row.get("购置时间") or "").strip()
        calibration_time = (row.get("校准时间") or "").strip()
        responsible = (row.get("责任人") or "").strip()
        equip_class = (row.get("分类") or "").strip()

        if not mgmt_no:
            continue

        existing = await db.execute(
            text("SELECT 1 FROM equipment_registry WHERE management_no=:m"),
            {"m": mgmt_no},
        )
        if existing.fetchone():
            await db.execute(
                text("""
                    UPDATE equipment_registry SET
                        equipment_name=:en, model=:md, measuring_range=:mr,
                        manufacturer=:mf, serial_no=:sn, purchase_time=:pd,
                        calibration_time=:ct, responsible=:rp, equipment_class=:ec,
                        lifecycle_status='启用', updated_at=localtimestamp
                    WHERE management_no=:mn
                """),
                {
                    "en": name, "md": model, "mr": measuring_range,
                    "mf": manufacturer, "sn": serial_no, "pd": purchase_time if purchase_time else None,
                    "ct": calibration_time if calibration_time else None, "rp": responsible,
                    "ec": equip_class, "mn": mgmt_no,
                },
            )
            updated += 1
        else:
            await db.execute(
                text("""
                    INSERT INTO equipment_registry (
                        management_no, equipment_name, model, measuring_range, manufacturer, serial_no,
                        purchase_time, calibration_time, responsible, equipment_class,
                        lifecycle_status, enabled, created_at, updated_at
                    ) VALUES (
                        :mn, :en, :md, :mr, :mf, :sn,
                        :pd, :ct, :rp, :ec,
                        '启用', TRUE, localtimestamp, localtimestamp
                    )
                """),
                {
                    "mn": mgmt_no, "en": name, "md": model, "mr": measuring_range,
                    "mf": manufacturer, "sn": serial_no,
                    "pd": purchase_time if purchase_time else None,
                    "ct": calibration_time if calibration_time else None,
                    "rp": responsible, "ec": equip_class,
                },
            )
            inserted += 1

    print(f"  Equipment: {inserted} inserted, {updated} updated")
    return inserted + updated


async def seed_equipment_bindings(db) -> int:
    await db.execute(text("DELETE FROM experiment_equipment_bindings"))
    count = 0
    with open(BINDING_CSV, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            experiment = (row.get("实验名称") or "").strip()
            mgmt_no = (row.get("管理编号") or "").strip()
            if not experiment or not mgmt_no:
                continue
            await db.execute(
                text("""
                    INSERT INTO experiment_equipment_bindings (
                        experiment, management_no, binding_role, required, note, created_at, updated_at
                    ) VALUES (:ex, :mn, :br, :rq, :nt, localtimestamp, localtimestamp)
                """),
                {
                    "ex": experiment,
                    "mn": mgmt_no,
                    "br": (row.get("设备角色") or "").strip(),
                    "rq": (row.get("是否必需") or "是").strip() == "是",
                    "nt": (row.get("用途/绑定说明") or "").strip(),
                },
            )
            count += 1
    print(f"  Bindings: {count} imported")
    return count


async def seed_experiment_configs(db) -> int:
    count = 0
    for code in ("I010", "I011", "I012", "I013", "I014"):
        existing = await db.execute(
            text("SELECT 1 FROM experiment_config_versions WHERE experiment_code=:c AND version='V2.0'"),
            {"c": code},
        )
        if not existing.fetchone():
            await db.execute(
                text("""
                    INSERT INTO experiment_config_versions (
                        experiment_code, version, status, created_at, updated_at
                    ) VALUES (:c, 'V2.0', '现行', localtimestamp, localtimestamp)
                """),
                {"c": code},
            )
            count += 1
            print(f"  Config created: {code} V2.0")
    return count


def copy_templates():
    if not TEMPLATE_SRC.exists():
        print("  Template source not found, skipping")
        return 0

    new_templates = [
        "R014_定制式固定义齿检验_CMA原始记录表.docx",
        "R015_定制式活动义齿检验_CMA原始记录表.docx",
        "R017_金属材料抗晦暗性能试验_CMA原始记录表.docx",
        "SOP-015_定制式活动义齿检验.docx",
        "SOP-011_维氏硬度试验.docx",
        "SOP-016_激光选区熔化金属材料密度试验.docx",
    ]
    updated_templates = [
        "R005_金属内部质量X射线灰度分析_CMA原始记录表.docx",
        "R006_翘曲变形试验_CMA原始记录表.docx",
        "R011_维氏硬度试验_CMA原始记录表.docx",
        "R013_增材制造金属试样厚度测量_CMA原始记录表.docx",
    ]

    os.makedirs(TEMPLATE_DST, exist_ok=True)
    copied = 0
    for fname in new_templates + updated_templates:
        src = TEMPLATE_SRC / fname
        dst = TEMPLATE_DST / fname
        if src.exists():
            shutil.copy2(src, dst)
            copied += 1
            print(f"  Copied: {fname}")
        else:
            print(f"  SKIP (not found): {fname}")

    print(f"  Templates: {copied} files copied")
    return copied


async def main():
    print("=" * 60)
    print("BPLab Trace V10.0 Seed Script")
    print("=" * 60)

    async with async_session() as db:
        try:
            print("\n[1/4] Seeding experiment_methods...")
            await seed_experiment_methods(db)
            await db.commit()

            print("\n[2/4] Seeding equipment_registry...")
            await seed_equipment(db)
            await db.commit()

            print("\n[3/4] Seeding experiment_equipment_bindings...")
            await seed_equipment_bindings(db)
            await db.commit()

            print("\n[4/4] Creating experiment_config_versions...")
            await seed_experiment_configs(db)
            await db.commit()

            print("\nAll database changes committed!")

        except Exception as e:
            await db.rollback()
            print(f"\nError: {e}")
            raise

    print("\n[5/5] Copying V10 templates...")
    copy_templates()

    # Verify
    print("\n" + "=" * 60)
    print("Verification:")
    async with async_session() as db:
        r = await db.execute(text("SELECT COUNT(*) FROM experiment_methods"))
        print(f"  experiment_methods: {r.fetchone()[0]} rows")
        r = await db.execute(text("SELECT COUNT(*) FROM equipment_registry"))
        print(f"  equipment_registry: {r.fetchone()[0]} rows")
        r = await db.execute(text("SELECT COUNT(*) FROM experiment_equipment_bindings"))
        print(f"  experiment_equipment_bindings: {r.fetchone()[0]} rows")
        r = await db.execute(
            text("SELECT experiment_code, experiment_name FROM experiment_methods ORDER BY experiment_code")
        )
        print("  Methods:")
        for row in r.fetchall():
            print(f"    {row[0]} = {row[1]}")
        await db.commit()

    print("\nDone! V10.0 seed complete.")


if __name__ == "__main__":
    asyncio.run(main())
