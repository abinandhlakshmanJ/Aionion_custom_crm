import frappe

def execute():
    now = frappe.utils.now_datetime()
    window_start = frappe.utils.add_to_date(now, minutes=-15)
    window_end = frappe.utils.add_to_date(now, minutes=75)

    print("Current time:", now)
    print("Window start:", window_start)
    print("Window end:", window_end)

    tasks = frappe.get_all(
        "CRM Task",
        filters=[
            ["due_date", ">=", window_start],
            ["due_date", "<", window_end],
            ["status", "not in", ["Done", "Cancelled"]]
        ],
        fields=["name", "title", "due_date", "assigned_to", "status"]
    )
    print("Found tasks:", tasks)
