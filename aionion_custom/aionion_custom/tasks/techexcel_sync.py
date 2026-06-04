import frappe
from frappe.utils import now_datetime
from frappe.utils.password import get_decrypted_password


def sync_customers_from_s3():
    """
    Daily scheduled job — pulls TechExcel client list from S3
    and upserts into Customer DocType.
    Called via hooks.py scheduler.
    """
    try:
        frappe.logger().info("TechExcel Sync: Starting...")

        settings = frappe.get_single("TechExcel Settings")

        if not settings.enabled:
            frappe.logger().info("TechExcel Sync: Disabled in settings, skipping.")
            return

        if not settings.aws_access_key_id:
            frappe.log_error("TechExcel Sync: AWS Access Key ID not configured.", "TechExcel Sync")
            return

        import boto3
        import json
        from datetime import datetime

        # Step 1: Connect to S3
        try:
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
            frappe.logger().info(f"TechExcel Sync: Loaded {len(all_data)} records from S3")
        except Exception as e:
            frappe.log_error(f"TechExcel Sync: S3 connection failed — {str(e)}", "TechExcel Sync")
            return

        # Step 2: Delta filter
        try:
            last_sync = settings.last_sync_datetime
            if last_sync:
                last_sync_str = str(last_sync)
                try:
                    last_sync_dt = datetime.strptime(last_sync_str, "%Y-%m-%d %H:%M:%S.%f")
                except ValueError:
                    last_sync_dt = datetime.strptime(last_sync_str, "%Y-%m-%d %H:%M:%S")
                data = [r for r in all_data if _is_modified_after(r, last_sync_dt)]
                frappe.logger().info(f"TechExcel Sync: Delta mode — {len(data)} records to process")
            else:
                data = all_data
                frappe.logger().info(f"TechExcel Sync: Full sync mode — {len(data)} records to process")
        except Exception as e:
            frappe.log_error(f"TechExcel Sync: Delta filter failed — {str(e)}", "TechExcel Sync")
            return

        # Step 3: Load existing customers into memory (avoids N+1)
        try:
            existing_customers = frappe.get_all(
                "Customer",
                filters={"custom_client_id": ["!=", ""]},
                fields=["name", "custom_client_id", "custom_aionion_master_id"],
                limit=0
            )
            existing_map = {c.custom_client_id: c for c in existing_customers}
            frappe.logger().info(f"TechExcel Sync: {len(existing_map)} existing customers loaded")
        except Exception as e:
            frappe.log_error(f"TechExcel Sync: Failed to load existing customers — {str(e)}", "TechExcel Sync")
            return

        # Step 4: Split into creates and updates
        to_create = []
        to_update = []
        for record in data:
            client_id = record.get("Client_ID")
            if not client_id:
                continue
            if client_id in existing_map:
                to_update.append(record)
            else:
                to_create.append(record)

        frappe.logger().info(f"TechExcel Sync: {len(to_create)} to create, {len(to_update)} to update")
        results = {"created": 0, "updated": 0, "errors": 0}

        # Step 5: Process CREATES first
        frappe.logger().info("TechExcel Sync: Starting creates...")
        for i, record in enumerate(to_create):
            try:
                _create_customer(record)
                results["created"] += 1
                if results["created"] % 100 == 0:
                    frappe.db.commit()
                    frappe.logger().info(f"TechExcel Sync: Created {results['created']}/{len(to_create)}")
            except Exception as e:
                results["errors"] += 1
                frappe.log_error(
                    f"TechExcel create error for {record.get('Client_ID')}: {str(e)}",
                    "TechExcel Customer Sync"
                )

        frappe.db.commit()
        frappe.logger().info(f"TechExcel Sync: Creates done — {results['created']} created, {results['errors']} errors")

        # Step 6: Process UPDATES in batches of 500
        frappe.logger().info("TechExcel Sync: Starting updates...")
        batch_size = 500
        for i in range(0, len(to_update), batch_size):
            batch = to_update[i:i + batch_size]
            try:
                _bulk_update_customers(batch, existing_map)
                results["updated"] += len(batch)
                frappe.db.commit()
                frappe.logger().info(f"TechExcel Sync: Updated {results['updated']}/{len(to_update)}")
            except Exception as e:
                results["errors"] += len(batch)
                frappe.log_error(
                    f"TechExcel bulk update error at batch {i}: {str(e)}",
                    "TechExcel Customer Sync"
                )

        # Step 7: Save final stats
        frappe.db.set_value("TechExcel Settings", "TechExcel Settings", {
            "last_sync_datetime": now_datetime(),
            "last_sync_created": results.get("created", 0),
            "last_sync_updated": results.get("updated", 0),
            "last_sync_errors": results.get("errors", 0),
        })
        frappe.db.commit()
        frappe.logger().info(f"TechExcel Sync Complete: {results}")

    except Exception as e:
        frappe.log_error(f"TechExcel Sync Failed: {str(e)}", "TechExcel Sync")


def _is_modified_after(record, last_sync_dt):
    from datetime import datetime
    last_modified = record.get("LAST_MODIFIED_DATE", "")
    if not last_modified:
        return True
    try:
        rec_dt = datetime.strptime(last_modified, "%Y-%m-%d %H:%M:%S.%f")
    except Exception:
        try:
            rec_dt = datetime.strptime(last_modified, "%Y-%m-%d %H:%M:%S")
        except Exception:
            return True
    return rec_dt > last_sync_dt


def _get_fields(record):
    from datetime import datetime

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

    return {
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


def _create_customer(record):
    from aionion_custom.aionion_custom.controllers.crm_lead import _generate_aionion_master_id
    fields = _get_fields(record)
    doc = frappe.get_doc({
        "doctype": "Customer",
        "customer_name": record.get("Client_Name"),
        "customer_type": "Individual",
        "customer_group": "Individual",
        "territory": "India",
        "custom_client_id": record.get("Client_ID"),
        **fields,
    })
    doc.insert(ignore_permissions=True, ignore_links=True)
    _generate_aionion_master_id(doc)


def _bulk_update_customers(batch, existing_map):
    from aionion_custom.aionion_custom.controllers.crm_lead import _generate_aionion_master_id
    for record in batch:
        client_id = record.get("Client_ID")
        existing = existing_map.get(client_id)
        if not existing:
            continue
        fields = _get_fields(record)
        frappe.db.set_value("Customer", existing.name, fields, update_modified=False)
        if not existing.custom_aionion_master_id:
            customer = frappe.get_doc("Customer", existing.name)
            _generate_aionion_master_id(customer)
