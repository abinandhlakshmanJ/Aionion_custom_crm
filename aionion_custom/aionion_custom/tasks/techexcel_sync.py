import frappe
from frappe.utils import now_datetime
from frappe.utils.password import get_decrypted_password


def sync_customers_from_s3():
    """
    Daily scheduled job — pulls TechExcel client list from S3
    and upserts into Customer DocType.
    Only processes records modified since last sync (delta sync).
    """
    try:
        settings = frappe.get_single("TechExcel Settings")

        if not settings.enabled:
            frappe.logger().info("TechExcel Sync: Disabled in settings, skipping.")
            return

        if not settings.aws_access_key_id:
            frappe.log_error("TechExcel Sync: AWS credentials not configured.", "TechExcel Sync")
            return

        import boto3
        import json
        from datetime import datetime

        s3 = boto3.client(
            "s3",
            region_name=settings.aws_region or "ap-south-1",
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=get_decrypted_password(
                "TechExcel Settings", "TechExcel Settings", "aws_secret_access_key"
            ),
        )

        response = s3.get_object(
            Bucket=settings.s3_bucket_name,
            Key=settings.s3_file_key or "techexcel/clients.json"
        )
        raw = response["Body"].read().decode("utf-8")
        all_data = json.loads(raw)

        # Delta sync — only process records modified since last sync
        last_sync = settings.last_sync_datetime
        if last_sync:
            last_sync_dt = last_sync if hasattr(last_sync, "strftime") else datetime.strptime(str(last_sync), "%Y-%m-%d %H:%M:%S.%f")
            data = []
            for record in all_data:
                last_modified = record.get("LAST_MODIFIED_DATE", "")
                if last_modified:
                    try:
                        rec_dt = datetime.strptime(last_modified, "%Y-%m-%d %H:%M:%S.%f")
                    except Exception:
                        try:
                            rec_dt = datetime.strptime(last_modified, "%Y-%m-%d %H:%M:%S")
                        except Exception:
                            rec_dt = None
                    if rec_dt and rec_dt > last_sync_dt:
                        data.append(record)
                else:
                    data.append(record)
        else:
            # First run — process all
            data = all_data

        total = len(data)
        frappe.logger().info(f"TechExcel Sync: {total} records to process (out of {len(all_data)} total)")
        print(f"TechExcel Sync: {total} records to process (out of {len(all_data)} total)")

        results = {"created": 0, "updated": 0, "skipped": 0, "errors": 0}

        for i, record in enumerate(data):
            try:
                result = _upsert_customer(record)
                results[result] = results.get(result, 0) + 1
            except Exception as e:
                results["errors"] += 1
                frappe.log_error(
                    f"TechExcel sync error for {record.get('Client_ID')}: {str(e)}",
                    "TechExcel Customer Sync"
                )

            if (i + 1) % 1000 == 0:
                print(f"Progress: {i+1}/{total} | {results}")

        frappe.db.set_value("TechExcel Settings", "TechExcel Settings", {
            "last_sync_datetime": now_datetime(),
            "last_sync_created": results.get("created", 0),
            "last_sync_updated": results.get("updated", 0),
            "last_sync_errors": results.get("errors", 0),
        })
        frappe.db.commit()

        print(f"TechExcel Sync Complete: {results}")
        frappe.logger().info(f"TechExcel Sync Complete: {results}")

    except Exception as e:
        frappe.log_error(f"TechExcel Sync Failed: {str(e)}", "TechExcel Sync")
        print(f"TechExcel Sync Failed: {str(e)}")


def _upsert_customer(record):
    from datetime import datetime
    from aionion_custom.aionion_custom.controllers.crm_lead import _generate_aionion_master_id

    def parse_date(date_str):
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str, "%d/%m/%Y").strftime("%Y-%m-%d")
        except Exception:
            return None

    def parse_datetime(dt_str):
        if not dt_str:
            return None
        try:
            return datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S.%f").strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            try:
                return datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                return None

    client_id = record.get("Client_ID")
    if not client_id:
        return "skipped"

    fields = {
        "custom_client_code":             record.get("Code"),
        "custom_pan":                     record.get("PAN_NO"),
        "custom_mobile":                  str(record.get("Mobile_No", "") or ""),
        "custom_email":                   record.get("Client_ID_Mail"),
        "custom_dob":                     parse_date(record.get("Birth_Date")),
        "custom_active_inactive":         record.get("ACTIVE_INACTIVE"),
        "custom_agreement_date":          parse_date(record.get("AGREEMENT_DATE")),
        "custom_techexcel_last_modified": parse_datetime(record.get("LAST_MODIFIED_DATE")),
        "custom_marital_status":          record.get("Marital_status"),
        "custom_occupation":              record.get("Occupation"),
        "custom_nationality":             record.get("NATIONALITY"),
        "custom_residential_address":     record.get("RESI_ADDRESS"),
        "custom_rm_name":                 record.get("RELATIONMANAGER_NAME"),
        "custom_rm_code":                 record.get("RELATIONMANAGER_CODE"),
        "custom_branch_code":             record.get("BRANCH_CODE"),
        "custom_branch_name":             record.get("BRANCH_NAME"),
        "custom_main_branch_code":        record.get("MAIN_BRANCH_CODE"),
        "custom_bank_account_no":         record.get("BANK_ACNO"),
        "custom_bank_name":               record.get("CLIENT_BANK_NAME"),
        "custom_micr_code":               record.get("MICR_CODE"),
        "custom_ifsc_code":               record.get("IFSCCODE"),
        "custom_account_category":        record.get("CATEGORY_DESC"),
    }

    existing = frappe.db.get_value(
        "Customer",
        {"custom_client_id": client_id},
        ["name", "custom_aionion_master_id"],
        as_dict=True,
    )

    if existing:
        frappe.db.set_value("Customer", existing.name, fields, update_modified=False)
        if not existing.custom_aionion_master_id:
            customer = frappe.get_doc("Customer", existing.name)
            _generate_aionion_master_id(customer)
        frappe.db.commit()
        return "updated"

    doc = frappe.get_doc({
        "doctype": "Customer",
        "customer_name": record.get("Client_Name"),
        "customer_type": "Individual",
        "customer_group": "Individual",
        "territory": "India",
        "custom_client_id": client_id,
        **fields,
    })
    doc.insert(ignore_permissions=True, ignore_links=True)
    _generate_aionion_master_id(doc)
    frappe.db.commit()
    return "created"
