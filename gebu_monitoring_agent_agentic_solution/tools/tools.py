# import os
# import smtplib
# import tempfile
# from datetime import UTC, datetime, timedelta
# from email.mime.multipart import MIMEMultipart
# from email.mime.text import MIMEText
# from pathlib import Path

# import google.auth
# import pandas as pd
# from dotenv import load_dotenv
# from google.cloud import firestore, storage
# from google.cloud import logging as cloud_logging

# # 1. Load .env File
# env_path = Path(__file__).resolve().parent.parent / ".env"
# load_dotenv(dotenv_path=env_path)

# # 2. Authentication & Infrastructure Clients
# _, default_project = google.auth.default()
# project_id = os.getenv("GOOGLE_CLOUD_PROJECT") or default_project

# os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
# os.environ["GOOGLE_CLOUD_LOCATION"] = os.getenv("GOOGLE_CLOUD_LOCATION", "global")
# os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "True")

# firestore_db_name = os.getenv("FIRESTORE_DATABASE", "drift-monitor")
# db = firestore.Client(project=project_id, database=firestore_db_name)
# storage_client = storage.Client(project=project_id)


# # FIRESTORE PERSISTENCE HELPERS
# def set_action_transitions(work_item_id: str, transitions: list[dict]):
#     """Persists pipeline transition states to the Firestore 'actions' collection."""
#     real_time = datetime.now(UTC).isoformat()
#     for t in transitions:
#         t["timestamp"] = real_time
#     actions_ref = db.collection("actions")
#     query = actions_ref.where("work_item_id", "==", work_item_id).limit(1).get()
#     status = (
#         "SUCCESS"
#         if all(t.get("status") == "SUCCESS" for t in transitions)
#         else "FAILED"
#     )
#     if not query:
#         new_doc_ref = actions_ref.document()
#         new_doc_ref.set(
#             {
#                 "action_id": new_doc_ref.id,
#                 "work_item_id": work_item_id,
#                 "agent_name": "RootAgent",
#                 "action_type": "DRIFT_DETECTION",
#                 "status": status,
#                 "summary": (
#                     "Processed work item drift telemetry."
#                     if status == "SUCCESS"
#                     else "Processing failed or skipped during verification."
#                 ),
#                 "timestamp": real_time,
#                 "transitions": transitions,
#             }
#         )
#     else:
#         doc_id = query[0].id
#         actions_ref.document(doc_id).set(
#             {"transitions": transitions, "status": status, "timestamp": real_time},
#             merge=True,
#         )


# def _get_incident_id(work_item_id: str) -> str:
#     """Internal helper to fetch the incident_id linked to a work_item_id from Firestore."""
#     for collection in ["work_items", "work_item"]:
#         ref = db.collection(collection).document(work_item_id)
#         doc = ref.get()
#         if doc.exists:
#             inc_id = doc.to_dict().get("incident_id")
#             if inc_id:
#                 return str(inc_id)
#     return "unknown-incident"


# def save_incident_enrichment(
#     work_item_id: str,
#     summary: str,
#     keyword_counts: dict,
#     severity_counts: dict,
#     total_entries_scanned: int,
# ) -> str:
#     """Helper to record evidence metadata inside the 'incident_enrichments' collection."""
#     scan_time = datetime.now(UTC).isoformat()
#     incident_id = _get_incident_id(str(work_item_id))
#     doc_id = f"{incident_id}{work_item_id}"
#     ref = db.collection("incident_enrichments").document(doc_id)
#     ref.set(
#         {
#             "work_item_id": str(work_item_id),
#             "summary": summary,
#             "keyword_counts": keyword_counts,
#             "severity_counts": severity_counts,
#             "total_entries_scanned": total_entries_scanned,
#             "created_at": scan_time,
#             "enrichment_creation_time": scan_time,
#         }
#     )
#     return ref.id


# def save_incident_summary(
#     work_item_id: str,
#     provider: str,
#     summary: str,
#     summary_preview: str,
#     provider_error: str,
# ) -> str:
#     """Helper to record AI summary reports inside the 'incident_summaries' collection."""
#     gen_time = datetime.now(UTC).isoformat()
#     incident_id = _get_incident_id(str(work_item_id))
#     doc_id = f"{incident_id}{work_item_id}"
#     ref = db.collection("incident_summaries").document(doc_id)
#     ref.set(
#         {
#             "work_item_id": str(work_item_id),
#             "provider": provider,
#             "summary": summary,
#             "summary_preview": summary_preview,
#             "provider_error": provider_error,
#             "created_at": gen_time,
#             "summary_creation_time": gen_time,
#         }
#     )
#     update_work_item_workflow_status(
#         work_item_id, enrichment_status="Done" if not provider_error else "NOT DONE"
#     )
#     return ref.id


# def update_work_item_workflow_status(
#     work_item_id: str,
#     enrichment_status: str | None = None,
#     notification_status: str | None = None,
# ) -> dict:
#     """Updates workflow tracking status fields inside the nested 'workflow' map in Firestore."""
#     ref = db.collection("work_items").document(work_item_id)
#     if not ref.get().exists:
#         ref = db.collection("work_item").document(work_item_id)

#     update_data = {}
#     if enrichment_status:
#         update_data["workflow.enrichment_status"] = enrichment_status
#     if notification_status:
#         update_data["workflow.notification_status"] = notification_status

#     if update_data:
#         update_data["updated_at"] = datetime.now(UTC).isoformat()
#         ref.update(update_data)
#         return {"status": "success", "updated_fields": list(update_data.keys())}
#     return {"status": "skipped", "message": "No status fields provided for update."}


# def record_notification_result(
#     notification_id: str,
#     incident_id: str,
#     work_item_id: str,
#     delivery_status: str,
#     recipients: list,
#     delivery_error: str,
#     subject: str,
# ) -> None:
#     """Helper to record notification delivery audit logs inside Firestore."""
#     data = {
#         "incident_id": incident_id,
#         "work_item_id": work_item_id,
#         "notification_id": notification_id,
#         "delivery_status": delivery_status,
#         "recipients": recipients,
#         "delivery_error": delivery_error,
#         "subject": subject,
#         "created_at": datetime.now(UTC).isoformat(),
#     }
#     if recipients:
#         data["owner_resolution"] = "UNRESOLVED"

#     db.collection("notifications").document(notification_id).set(data)
#     update_work_item_workflow_status(work_item_id, notification_status=delivery_status)


# # TOOL DEFINITIONS & KEYWORD DICTIONARIES

# CPU_DRIFT_KEYWORDS = [
#     "FailedScheduling",
#     "Insufficient cpu",
#     "didn't have enough cpu",
#     "FailedScaleUp",
#     "NotTriggerScaleUp",
#     "NoScaleUp",
#     "Cluster autoscaler",
#     "ScaleUp",
#     "ScaleDown",
#     "OOMKilled",
#     "Evicted",
#     "NodeNotReady",
#     "NodeHasInsufficientCPU",
#     "NodeHasMemoryPressure",
#     "NodeHasDiskPressure",
#     "NodeHasPIDPressure",
#     "CrashLoopBackOff",
#     "BackOff",
#     "Back-off restarting failed container",
#     "Killing",
#     "ContainerCannotRun",
#     "CreateContainerError",
#     "RunContainerError",
#     "StartError",
#     "Unhealthy",
#     "Liveness probe failed",
#     "Readiness probe failed",
#     "Startup probe failed",
#     "CPUThrottlingHigh",
#     "cpu throttling",
#     "throttled",
#     "GCE quota exceeded",
#     "Quota exceeded",
#     "RESOURCE_EXHAUSTED",
#     "Error",
#     "Warning",
#     "OutOfCPU",
# ]


# def validate_work_item(work_item_id: str) -> dict:
#     """Validates that a work item exists in Firestore and checks if its linked incident also exists."""
#     work_item_doc = None

#     for collection in ["work_items", "work_item"]:
#         ref = db.collection(collection).document(work_item_id)
#         doc = ref.get()
#         if doc.exists and doc.to_dict().get("incident_id"):
#             work_item_doc = doc
#             break
#         elif doc.exists and not work_item_doc:
#             work_item_doc = doc

#     if not work_item_doc or not work_item_doc.exists:
#         return {
#             "status": "invalid",
#             "reason": f"Work item {work_item_id} does not exist in Firestore.",
#         }

#     work_item_data = work_item_doc.to_dict()
#     incident_id = work_item_data.get("incident_id")

#     if not incident_id:
#         return {
#             "status": "invalid",
#             "reason": f"Work item {work_item_id} is missing linked 'incident_id'.",
#         }

#     incident_doc = None
#     for collection in ["incidents", "incident"]:
#         ref = db.collection(collection).document(incident_id)
#         doc = ref.get()
#         if doc.exists:
#             incident_doc = doc
#             break

#     if not incident_doc or not incident_doc.exists:
#         return {
#             "status": "invalid",
#             "reason": f"Incident {incident_id} linked to work item {work_item_id} does not exist.",
#         }

#     incident_data = incident_doc.to_dict()
#     cluster_name = (
#         incident_data.get("cluster")
#         or incident_data.get("cluster_name")
#         or "unknown-cluster"
#     )
#     node_pool = (
#         incident_data.get("nodepool")
#         or incident_data.get("node_pool")
#         or "default-pool"
#     )

#     result = {
#         "status": "valid",
#         "work_item_id": str(work_item_id),
#         "incident_id": str(incident_id),
#         "cluster_name": cluster_name,
#         "node_pool": node_pool,
#     }

#     for k, v in incident_data.items():
#         if k not in result:
#             result[k] = v

#     for k, v in work_item_data.items():
#         if k == "status":
#             result["work_item_status"] = v
#         elif k not in result:
#             result[k] = v

#     return result


# def fetch_cluster_logs(work_item_details: dict) -> dict:
#     """Step 1 Tool: Connects to Cloud Logging, extracts raw log blocks,
#     dynamically scans for static and runtime keywords/reasons,
#     calculates counts, and records evidence inside 'incident_enrichments'.
#     """
#     work_item_id = work_item_details.get("work_item_id")
#     cluster_name = (
#         work_item_details.get("cluster_name")
#         or work_item_details.get("cluster")
#         or "unknown-cluster"
#     )
#     target_project = work_item_details.get("project_id") or project_id
#     location = work_item_details.get("region") or work_item_details.get(
#         "location", "us-central1"
#     )
#     resource_type = work_item_details.get("resource_type", "k8s_cluster")
#     node_pool = work_item_details.get("node_pool") or work_item_details.get("nodepool")

#     total_scanned = 0
#     raw_log_text = ""
#     severity_counts = {"ERROR": 0, "WARNING": 0, "CRITICAL": 0, "INFO": 0}
#     keyword_counts = dict.fromkeys(CPU_DRIFT_KEYWORDS, 0)

#     dynamic_perf_terms = [
#         "cpu",
#         "memory",
#         "utilization",
#         "load",
#         "latency",
#         "delay",
#         "timeout",
#         "saturated",
#         "throttled",
#         "restarting",
#         "unhealthy",
#         "probe",
#         "scaled",
#         "pending",
#         "failed",
#         "killed",
#         "high",
#         "spike",
#         "exhausted",
#         "queue",
#         "pressure",
#         "slow",
#         "backoff",
#     ]

#     logging_client = cloud_logging.Client(project=target_project)
#     one_hour_ago = (datetime.utcnow() - timedelta(hours=48)).isoformat() + "Z"

#     if resource_type == "k8s_cluster":
#         resource_filter = '(resource.type="k8s_cluster" OR resource.type="k8s_node" OR resource.type="k8s_pod" OR resource.type="k8s_container")'
#     else:
#         resource_filter = f'resource.type="{resource_type}"'

#     log_filter = (
#         f"{resource_filter} "
#         f'resource.labels.cluster_name="{cluster_name}" '
#         f'resource.labels.location="{location}" '
#     )
#     if node_pool:
#         log_filter += f'resource.labels.nodepool_id="{node_pool}" '

#     log_filter += f'severity>=WARNING timestamp>="{one_hour_ago}"'
#     entries = logging_client.list_entries(
#         filter_=log_filter, page_size=100, max_results=100
#     )

#     for entry in entries:
#         if total_scanned >= 100:
#             break
#         total_scanned += 1
#         payload = entry.payload if entry.payload else entry.text_payload
#         sev = entry.severity if entry.severity else "INFO"

#         severity_counts[sev] = severity_counts.get(sev, 0) + 1
#         payload_str = str(payload).lower()

#         for kw in CPU_DRIFT_KEYWORDS:
#             if kw.lower() in payload_str:
#                 keyword_counts[kw] += 1

#         for term in dynamic_perf_terms:
#             if term in payload_str:
#                 kw_label = f"dynamic:{term}"
#                 keyword_counts[kw_label] = keyword_counts.get(kw_label, 0) + 1

#         if isinstance(payload, dict):
#             reason = (
#                 payload.get("reason")
#                 or payload.get("Reason")
#                 or payload.get("event")
#                 or payload.get("Event")
#                 or payload.get("component")
#                 or payload.get("Component")
#             )
#             if reason and isinstance(reason, str):
#                 kw_label = f"reason:{reason.strip()}"
#                 keyword_counts[kw_label] = keyword_counts.get(kw_label, 0) + 1

#         raw_log_text += f"[{entry.timestamp}] {sev}: {payload}\n"

#     if work_item_id:
#         non_zero_kws = {k: v for k, v in keyword_counts.items() if v > 0}
#         if non_zero_kws:
#             summary_msg = f"Retrieved {total_scanned} log entries from cluster {cluster_name}. Key detected signals: {non_zero_kws}."
#         else:
#             summary_msg = f"Retrieved {total_scanned} log entries from cluster {cluster_name} over the past lookback period."

#         save_incident_enrichment(
#             str(work_item_id),
#             summary_msg,
#             keyword_counts,
#             severity_counts,
#             total_scanned,
#         )

#     return {
#         "project_id": target_project,
#         "location": location,
#         "cluster_name": cluster_name,
#         "total_entries_scanned": total_scanned,
#         "severity_counts": severity_counts,
#         "keyword_counts": keyword_counts,
#         "raw_logs_payload": (
#             raw_log_text if raw_log_text else "No error or warning logs found."
#         ),
#     }


# def store_incident_enrichment(
#     work_item_id: str,
#     summary: str,
#     keyword_counts: dict,
#     severity_counts: dict,
#     total_entries_scanned: int,
# ) -> dict:
#     """Tool wrapper around save_incident_enrichment."""
#     doc_id = save_incident_enrichment(
#         work_item_id, summary, keyword_counts, severity_counts, total_entries_scanned
#     )
#     return {"status": "success", "id": doc_id}


# def store_incident_summary(
#     work_item_id: str,
#     provider: str,
#     summary: str,
#     summary_preview: str,
#     provider_error: str,
# ) -> dict:
#     """Tool wrapper around save_incident_summary."""
#     doc_id = save_incident_summary(
#         work_item_id, provider, summary, summary_preview, provider_error
#     )
#     return {"status": "success", "id": doc_id}


# def update_action_transitions(work_item_id: str, transitions: list[dict]) -> dict:
#     """Tool wrapper around set_action_transitions."""
#     set_action_transitions(work_item_id, transitions)
#     return {"status": "success"}


# def _get_cluster_owner_email(cluster_name: str) -> str:
#     """Helper to retrieve the owner's email address from the mapping Excel in GCS."""
#     bucket_name = os.getenv("GCS_OWNER_MAPPING_BUCKET", "lbg-test-pradeep")
#     blob_name = os.getenv("GCS_OWNER_MAPPING_BLOB", "owner_mapping.xlsx")

#     bucket = storage_client.bucket(bucket_name)
#     blob = bucket.blob(blob_name)

#     if not blob.exists():
#         print(f"Owner mapping file gs://{bucket_name}/{blob_name} does not exist.")
#         return None

#     with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
#         tmp_path = tmp.name
#         blob.download_to_filename(tmp_path)

#     df = pd.read_excel(tmp_path)
#     df.columns = [col.strip().lower() for col in df.columns]

#     cluster_col = next((col for col in df.columns if "cluster" in col), None)
#     owner_col = next(
#         (col for col in df.columns if "owner" in col or "email" in col), None
#     )

#     if not cluster_col or not owner_col:
#         print(
#             "Excel columns must contain fields matching 'cluster' and 'owner' or 'email'."
#         )
#         return None

#     row = df[df[cluster_col].astype(str).str.lower() == cluster_name.lower()]
#     if not row.empty:
#         return str(row.iloc[0][owner_col]).strip()
#     return None


# def send_incident_email_notification(
#     work_item_id: str, cluster_name: str, summary_content: str
# ) -> dict:
#     """Notification Tool: Resolves cluster owner email from GCS, sends SRE summary report via SMTP,
#     and records results via persistence helper.
#     """
#     incident_id = _get_incident_id(work_item_id)
#     notification_id = f"notif_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
#     subject = f"[ALERT] CPU Drift Detected - GKE Cluster: {cluster_name}"

#     owner_email = _get_cluster_owner_email(cluster_name)
#     if not owner_email:
#         err_msg = (
#             f"No mapped owner email address found in Excel for cluster: {cluster_name}"
#         )
#         record_notification_result(
#             notification_id, incident_id, work_item_id, "FAILED", [], err_msg, subject
#         )
#         return {"status": "failed", "error": err_msg}

#     smtp_host = os.getenv("SMTP_HOST", "localhost")
#     try:
#         smtp_port = int(os.getenv("SMTP_PORT", "25"))
#     except ValueError:
#         smtp_port = 25
#     smtp_user = os.getenv("SMTP_USERNAME", "")
#     smtp_pass = os.getenv("SMTP_PASSWORD", "")
#     smtp_from = os.getenv("SMTP_FROM_EMAIL", "")

#     msg = MIMEMultipart()
#     msg["From"] = smtp_from
#     msg["To"] = owner_email
#     msg["Subject"] = subject
#     msg.attach(MIMEText(summary_content, "plain"))

#     with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
#         if smtp_user and smtp_pass:
#             server.ehlo()
#             server.starttls()
#             server.ehlo()
#             server.login(smtp_user, smtp_pass)
#         server.sendmail(smtp_from, [owner_email], msg.as_string())

#     record_notification_result(
#         notification_id, incident_id, work_item_id, "SENT", [owner_email], "", subject
#     )
#     return {
#         "status": "success",
#         "recipient": owner_email,
#         "notification_id": notification_id,
#     }


import os
import smtplib
import tempfile
import json
import uuid
import re
from datetime import UTC, datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import google.auth
import pandas as pd
from dotenv import load_dotenv
from google.cloud import storage
from google.cloud import logging as cloud_logging

# ---------------------------------------------------------
# CLOUD SQL SETUP (GCP NATIVE)
# ---------------------------------------------------------
# We use the GCP-native Cloud SQL Python Connector (google-cloud-sql-connector) 
# instead of standard SQLAlchemy + psycopg2, as it natively handles IAM auth, 
# IAM proxying, and SSL without needing external proxies or hardcoded passwords.
from google.cloud.sql.connector import Connector, IPTypes
import pg8000
import sqlalchemy
from sqlalchemy import text

# from app.guardrails import apply_all_guardrails

# 1. Load .env File
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# 2. Authentication & Infrastructure Clients
_, default_project = google.auth.default()
project_id = os.getenv("GOOGLE_CLOUD_PROJECT") or default_project

os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
os.environ["GOOGLE_CLOUD_LOCATION"] = os.getenv("GOOGLE_CLOUD_LOCATION", "global")
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "True")

storage_client = storage.Client(project=project_id)

DB_USER = os.getenv("DB_USER", "drift_admin")
DB_PASS = os.getenv("DB_PASS", "Hcltech@123")
DB_NAME = os.getenv("DB_NAME", "drift-monitor")
DB_SCHEMA = os.getenv("DB_SCHEMA", "drift_monitor_schema")
INSTANCE_CONNECTION_NAME = os.getenv("INSTANCE_CONNECTION_NAME", f"{project_id}:us-central1:drift-monitor-db")

# connector = Connector()
connector = Connector()

def getconn() -> pg8000.dbapi.Connection:
    """Callback function used by SQLAlchemy to fetch a connection via the GCP native connector."""
    conn: pg8000.dbapi.Connection = connector.connect(
        INSTANCE_CONNECTION_NAME,
        "pg8000",
        user=DB_USER,
        password=DB_PASS,
        db=DB_NAME,
        # ip_type=IPTypes.PUBLIC,  # Change to IPTypes.PRIVATE if running inside a VPC without public IP
        ip_type=IPTypes.PRIVATE,
    )
    return conn

# Create the SQLAlchemy engine using the GCP native connector callback
engine = sqlalchemy.create_engine(
    "postgresql+pg8000://",
    creator=getconn,
)


# ---------------------------------------------------------
# CLOUD SQL PERSISTENCE HELPERS
# ---------------------------------------------------------
def set_action_transitions(work_item_id: str, transitions: list[dict]):
    """Persists pipeline transition states to the Cloud SQL 'actions' table."""
    real_time = datetime.now(UTC).isoformat()
    for t in transitions:
        t["timestamp"] = real_time
        
    status = "SUCCESS" if all(t.get("status") == "SUCCESS" for t in transitions) else "FAILED"
    transitions_json = json.dumps(transitions)
    
    with engine.begin() as conn:
        query = text(f"SELECT action_id FROM {DB_SCHEMA}.actions WHERE work_item_id = :work_item_id LIMIT 1")
        result = conn.execute(query, {"work_item_id": work_item_id}).fetchone()
        
        if not result:
            action_id = str(uuid.uuid4())
            summary = "Processed work item drift telemetry." if status == "SUCCESS" else "Processing failed or skipped during verification."
            insert_query = text(f'''
                INSERT INTO {DB_SCHEMA}.actions 
                (action_id, work_item_id, agent_name, action_type, status, summary, timestamp, transitions)
                VALUES (:action_id, :work_item_id, 'RootAgent', 'DRIFT_DETECTION', :status, :summary, :timestamp, :transitions)
            ''')
            conn.execute(insert_query, {
                "action_id": action_id,
                "work_item_id": work_item_id,
                "status": status,
                "summary": summary,
                "timestamp": real_time,
                "transitions": transitions_json
            })
        else:
            action_id = result[0]
            update_query = text(f'''
                UPDATE {DB_SCHEMA}.actions 
                SET transitions = :transitions, status = :status, timestamp = :timestamp
                WHERE action_id = :action_id
            ''')
            conn.execute(update_query, {
                "transitions": transitions_json,
                "status": status,
                "timestamp": real_time,
                "action_id": action_id
            })


def _get_incident_id(work_item_id: str) -> str:
    """Internal helper to fetch the incident_id linked to a work_item_id from Cloud SQL."""
    with engine.connect() as conn:
        query = text(f"SELECT incident_id FROM {DB_SCHEMA}.work_items WHERE work_item_id = :work_item_id")
        result = conn.execute(query, {"work_item_id": work_item_id}).fetchone()
        if result and result[0]:
            return str(result[0])
    return "unknown-incident"


def save_incident_enrichment(
    work_item_id: str,
    summary: str,
    keyword_counts: dict,
    severity_counts: dict,
    total_entries_scanned: int,
) -> str:
    """Helper to record evidence metadata inside the 'incident_enrichments' table."""
    scan_time = datetime.now(UTC).isoformat()
    incident_id = _get_incident_id(str(work_item_id))
    enrichment_id = f"{incident_id}{work_item_id}"
    
    with engine.begin() as conn:
        insert_query = text(f'''
            INSERT INTO {DB_SCHEMA}.incident_enrichments 
            (enrichment_id, work_item_id, summary, keyword_counts, severity_counts, total_entries_scanned, created_at, enrichment_creation_time)
            VALUES (:enrichment_id, :work_item_id, :summary, :keyword_counts, :severity_counts, :total_entries_scanned, :created_at, :enrichment_creation_time)
            ON CONFLICT (enrichment_id) DO UPDATE SET
            summary = EXCLUDED.summary,
            keyword_counts = EXCLUDED.keyword_counts,
            severity_counts = EXCLUDED.severity_counts,
            total_entries_scanned = EXCLUDED.total_entries_scanned,
            enrichment_creation_time = EXCLUDED.enrichment_creation_time
        ''')
        conn.execute(insert_query, {
            "enrichment_id": enrichment_id,
            "work_item_id": str(work_item_id),
            "summary": summary,
            "keyword_counts": json.dumps(keyword_counts),
            "severity_counts": json.dumps(severity_counts),
            "total_entries_scanned": total_entries_scanned,
            "created_at": scan_time,
            "enrichment_creation_time": scan_time
        })
    return enrichment_id


def save_incident_summary(
    work_item_id: str,
    provider: str,
    summary: str,
    summary_preview: str,
    provider_error: str,
) -> str:
    """Helper to record AI summary reports inside the 'incident_summaries' table."""
    gen_time = datetime.now(UTC).isoformat()
    incident_id = _get_incident_id(str(work_item_id))
    summary_id = f"{incident_id}{work_item_id}"
    
    with engine.begin() as conn:
        insert_query = text(f'''
            INSERT INTO {DB_SCHEMA}.incident_summaries 
            (summary_id, work_item_id, provider, summary, summary_preview, provider_error, created_at, summary_creation_time)
            VALUES (:summary_id, :work_item_id, :provider, :summary, :summary_preview, :provider_error, :created_at, :summary_creation_time)
            ON CONFLICT (summary_id) DO UPDATE SET
            provider = EXCLUDED.provider,
            summary = EXCLUDED.summary,
            summary_preview = EXCLUDED.summary_preview,
            provider_error = EXCLUDED.provider_error,
            summary_creation_time = EXCLUDED.summary_creation_time
        ''')
        conn.execute(insert_query, {
            "summary_id": summary_id,
            "work_item_id": str(work_item_id),
            "provider": provider,
            "summary": summary,
            "summary_preview": summary_preview,
            "provider_error": provider_error or "",
            "created_at": gen_time,
            "summary_creation_time": gen_time
        })
        
    update_work_item_workflow_status(
        work_item_id, enrichment_status="Done" if not provider_error else "NOT DONE"
    )
    
    # Proactive transition update on successful summary save
    try:
        status_to_set = "SUCCESS" if not provider_error else "FAILED"
        set_action_transitions(work_item_id, [
            {"agent_name": "validation_agent", "status": "SUCCESS"},
            {"agent_name": "enrichment_agent", "status": status_to_set},
            {"agent_name": "notification_agent", "status": "PENDING" if not provider_error else "FAILED"}
        ])
    except Exception as trans_err:
        print(f"Warning: Failed to update transitions during enrichment: {trans_err}")

    return summary_id


def update_work_item_workflow_status(
    work_item_id: str,
    enrichment_status: str | None = None,
    notification_status: str | None = None,
) -> dict:
    """Updates workflow tracking status fields inside Cloud SQL work_items table."""
    updates = []
    params = {"work_item_id": work_item_id, "updated_at": datetime.now(UTC).isoformat()}
    
    if enrichment_status:
        updates.append("workflow_enrichment_status = :enrichment_status")
        params["enrichment_status"] = enrichment_status
    if notification_status:
        updates.append("workflow_notification_status = :notification_status")
        params["notification_status"] = notification_status
        
    if not updates:
        return {"status": "skipped", "message": "No status fields provided for update."}
        
    updates.append("updated_at = :updated_at")
    set_clause = ", ".join(updates)
    
    with engine.begin() as conn:
        update_query = text(f"UPDATE {DB_SCHEMA}.work_items SET {set_clause} WHERE work_item_id = :work_item_id")
        result = conn.execute(update_query, params)
        
        if result.rowcount > 0:
            return {"status": "success", "updated_fields": [k for k in params.keys() if k not in ("work_item_id", "updated_at")]}
        
    return {"status": "skipped", "message": "Work item not found in DB."}


def record_notification_result(
    incident_id: str,
    work_item_id: str,
    delivery_status: str,
    recipients: list,
    delivery_error: str,
    subject: str,
) -> str:
    """Helper to record notification delivery audit logs inside Cloud SQL."""
    created_at = datetime.now(UTC).isoformat()
    notification_id = f"{incident_id}{work_item_id}"
    
    with engine.begin() as conn:
        insert_query = text(f'''
            INSERT INTO {DB_SCHEMA}.notifications
            (notification_id, incident_id, work_item_id, delivery_status, recipients, delivery_error, subject, created_at)
            VALUES (:notification_id, :incident_id, :work_item_id, :delivery_status, :recipients, :delivery_error, :subject, :created_at)
            ON CONFLICT (notification_id) DO UPDATE SET
            delivery_status = EXCLUDED.delivery_status,
            recipients = EXCLUDED.recipients,
            delivery_error = EXCLUDED.delivery_error,
            subject = EXCLUDED.subject
        ''')
        conn.execute(insert_query, {
            "notification_id": notification_id,
            "incident_id": incident_id,
            "work_item_id": work_item_id,
            "delivery_status": delivery_status,
            "recipients": recipients,
            "delivery_error": delivery_error or "",
            "subject": subject,
            "created_at": created_at
        })

    update_work_item_workflow_status(work_item_id, notification_status=delivery_status)

    # Proactive transition update
    try:
        notif_status = "SUCCESS" if delivery_status == "SENT" else "FAILED"
        set_action_transitions(work_item_id, [
            {"agent_name": "validation_agent", "status": "SUCCESS"},
            {"agent_name": "enrichment_agent", "status": "SUCCESS"},
            {"agent_name": "notification_agent", "status": notif_status}
        ])
    except Exception as trans_err:
        print(f"Warning: Failed to update transitions during notification recording: {trans_err}")
        
    return notification_id

# TOOL DEFINITIONS & KEYWORD DICTIONARIES

CPU_DRIFT_KEYWORDS = [
    "FailedScheduling",
    "Insufficient cpu",
    "didn't have enough cpu",
    "FailedScaleUp",
    "NotTriggerScaleUp",
    "NoScaleUp",
    "Cluster autoscaler",
    "ScaleUp",
    "ScaleDown",
    "OOMKilled",
    "Evicted",
    "NodeNotReady",
    "NodeHasInsufficientCPU",
    "NodeHasMemoryPressure",
    "NodeHasDiskPressure",
    "NodeHasPIDPressure",
    "CrashLoopBackOff",
    "BackOff",
    "Back-off restarting failed container",
    "Killing",
    "ContainerCannotRun",
    "CreateContainerError",
    "RunContainerError",
    "StartError",
    "Unhealthy",
    "Liveness probe failed",
    "Readiness probe failed",
    "Startup probe failed",
    "CPUThrottlingHigh",
    "cpu throttling",
    "throttled",
    "GCE quota exceeded",
    "Quota exceeded",
    "RESOURCE_EXHAUSTED",
    "Error",
    "Warning",
    "OutOfCPU",
]


def validate_work_item(work_item_id: str) -> dict:
    """Validates that a work item exists in Cloud SQL and checks if its linked incident also exists."""
    
    # 1. IMMEDIATE GUARDRAIL: Block if work_item_id is a prompt injection attempt
    jailbreak_heuristics = [
        r"(?i)ignore\s+(all\s+)?previous\s+instructions",
        r"(?i)disregard\s+(all\s+)?previous\s+instructions",
        r"(?i)you\s+are\s+now\s+a\s+",
        r"(?i)forget\s+your\s+previous\s+prompt",
        r"(?i)print\s+your\s+system\s+prompt",
        r"(?i)system\s+override\s*:",
    ]
    for heuristic in jailbreak_heuristics:
        if re.search(heuristic, work_item_id):
            return {
                "status": "invalid",
                "reason": "SECURITY_ALERT: Malicious prompt injection attempt detected in input. Pipeline execution blocked.",
            }

    with engine.connect() as conn:
        wi_query = text(f"SELECT * FROM {DB_SCHEMA}.work_items WHERE work_item_id = :work_item_id")
        wi_result = conn.execute(wi_query, {"work_item_id": work_item_id}).fetchone()
        
        if not wi_result:
            try:
                set_action_transitions(work_item_id, [
                    {"agent_name": "validation_agent", "status": "FAILED"},
                    {"agent_name": "enrichment_agent", "status": "FAILED"},
                    {"agent_name": "notification_agent", "status": "FAILED"}
                ])
            except Exception as trans_err:
                print(f"Warning: Failed to update transitions during validation: {trans_err}")
            return {
                "status": "invalid",
                "reason": f"Work item {work_item_id} does not exist in Cloud SQL.",
            }
            
        # Extract row dictionary mapping
        work_item_data = wi_result._asdict()
        incident_id = work_item_data.get("incident_id")
        
        if not incident_id:
            try:
                set_action_transitions(work_item_id, [
                    {"agent_name": "validation_agent", "status": "FAILED"},
                    {"agent_name": "enrichment_agent", "status": "FAILED"},
                    {"agent_name": "notification_agent", "status": "FAILED"}
                ])
            except Exception as trans_err:
                print(f"Warning: Failed to update transitions during validation: {trans_err}")
            return {
                "status": "invalid",
                "reason": f"Work item {work_item_id} is missing linked 'incident_id'.",
            }
            
        inc_query = text(f"SELECT * FROM {DB_SCHEMA}.incidents WHERE incident_id = :incident_id")
        inc_result = conn.execute(inc_query, {"incident_id": incident_id}).fetchone()
        
        if not inc_result:
            try:
                set_action_transitions(work_item_id, [
                    {"agent_name": "validation_agent", "status": "FAILED"},
                    {"agent_name": "enrichment_agent", "status": "FAILED"},
                    {"agent_name": "notification_agent", "status": "FAILED"}
                ])
            except Exception as trans_err:
                print(f"Warning: Failed to update transitions during validation: {trans_err}")
            return {
                "status": "invalid",
                "reason": f"Incident {incident_id} linked to work item {work_item_id} does not exist.",
            }
            
        incident_data = inc_result._asdict()

    cluster_name = (
        incident_data.get("cluster")
        or incident_data.get("cluster_name")
        or "unknown-cluster"
    )
    node_pool = (
        incident_data.get("nodepool")
        or incident_data.get("node_pool")
        or "default-pool"
    )

    result = {
        "status": "valid",
        "work_item_id": str(work_item_id),
        "incident_id": str(incident_id),
        "cluster_name": cluster_name,
        "node_pool": node_pool,
    }

    for k, v in incident_data.items():
        if k not in result:
            result[k] = v

    for k, v in work_item_data.items():
        if k == "status":
            result["work_item_status"] = v
        elif k not in result:
            result[k] = v

    # Proactive transition update
    try:
        set_action_transitions(work_item_id, [
            {"agent_name": "validation_agent", "status": "SUCCESS"},
            {"agent_name": "enrichment_agent", "status": "PENDING"},
            {"agent_name": "notification_agent", "status": "PENDING"}
        ])
    except Exception as trans_err:
        print(f"Warning: Failed to update transitions during validation: {trans_err}")

    return result


def fetch_cluster_logs(work_item_details: dict) -> dict:
    """Step 1 Tool: Connects to Cloud Logging, extracts raw log blocks,
    dynamically scans for static and runtime keywords/reasons,
    calculates counts, and records evidence inside 'incident_enrichments'.
    """
    work_item_id = work_item_details.get("work_item_id")
    cluster_name = (
        work_item_details.get("cluster_name")
        or work_item_details.get("cluster")
        or "unknown-cluster"
    )
    target_project = work_item_details.get("project_id") or project_id
    location = work_item_details.get("region") or work_item_details.get(
        "location", "us-central1"
    )
    resource_type = work_item_details.get("resource_type", "k8s_cluster")
    node_pool = work_item_details.get("node_pool") or work_item_details.get("nodepool")

    total_scanned = 0
    raw_log_text = ""
    severity_counts = {"ERROR": 0, "WARNING": 0, "CRITICAL": 0, "INFO": 0}
    keyword_counts = dict.fromkeys(CPU_DRIFT_KEYWORDS, 0)

    dynamic_perf_terms = [
        "cpu",
        "memory",
        "utilization",
        "load",
        "latency",
        "delay",
        "timeout",
        "saturated",
        "throttled",
        "restarting",
        "unhealthy",
        "probe",
        "scaled",
        "pending",
        "failed",
        "killed",
        "high",
        "spike",
        "exhausted",
        "queue",
        "pressure",
        "slow",
        "backoff",
    ]

    logging_client = cloud_logging.Client(project=target_project)
    one_hour_ago = (datetime.utcnow() - timedelta(hours=48)).isoformat() + "Z"

    if resource_type == "k8s_cluster":
        resource_filter = '(resource.type="k8s_cluster" OR resource.type="k8s_node" OR resource.type="k8s_pod" OR resource.type="k8s_container")'
    else:
        resource_filter = f'resource.type="{resource_type}"'

    log_filter = (
        f"{resource_filter} "
        f'resource.labels.cluster_name="{cluster_name}" '
        f'resource.labels.location="{location}" '
    )
    if node_pool:
        log_filter += f'resource.labels.nodepool_id="{node_pool}" '

    log_filter += f'severity>=WARNING timestamp>="{one_hour_ago}"'
    entries = logging_client.list_entries(
        filter_=log_filter, page_size=100, max_results=100
    )

    for entry in entries:
        if total_scanned >= 100:
            break
        total_scanned += 1
        payload = entry.payload if entry.payload else entry.text_payload
        sev = entry.severity if entry.severity else "INFO"

        severity_counts[sev] = severity_counts.get(sev, 0) + 1
        payload_str = str(payload).lower()

        for kw in CPU_DRIFT_KEYWORDS:
            if kw.lower() in payload_str:
                keyword_counts[kw] += 1

        for term in dynamic_perf_terms:
            if term in payload_str:
                kw_label = f"dynamic:{term}"
                keyword_counts[kw_label] = keyword_counts.get(kw_label, 0) + 1

        if isinstance(payload, dict):
            reason = (
                payload.get("reason")
                or payload.get("Reason")
                or payload.get("event")
                or payload.get("Event")
                or payload.get("component")
                or payload.get("Component")
            )
            if reason and isinstance(reason, str):
                kw_label = f"reason:{reason.strip()}"
                keyword_counts[kw_label] = keyword_counts.get(kw_label, 0) + 1

        raw_log_text += f"[{entry.timestamp}] {sev}: {payload}\n"

    if work_item_id:
        non_zero_kws = {k: v for k, v in keyword_counts.items() if v > 0}
        if non_zero_kws:
            summary_msg = f"Retrieved {total_scanned} log entries from cluster {cluster_name}. Key detected signals: {non_zero_kws}."
        else:
            summary_msg = f"Retrieved {total_scanned} log entries from cluster {cluster_name} over the past lookback period."

        save_incident_enrichment(
            str(work_item_id),
            summary_msg,
            keyword_counts,
            severity_counts,
            total_scanned,
        )

    # SECURE THE PAYLOAD: Redact PII/Secrets and sanitize jailbreak/prompt injection attempts
    # raw_log_text = apply_all_guardrails(raw_log_text)

    return {
        "project_id": target_project,
        "location": location,
        "cluster_name": cluster_name,
        "total_entries_scanned": total_scanned,
        "severity_counts": severity_counts,
        "keyword_counts": keyword_counts,
        "raw_logs_payload": (
            raw_log_text if raw_log_text else "No error or warning logs found."
        ),
    }


def store_incident_enrichment(
    work_item_id: str,
    summary: str,
    keyword_counts: dict,
    severity_counts: dict,
    total_entries_scanned: int,
) -> dict:
    """Tool wrapper around save_incident_enrichment."""
    doc_id = save_incident_enrichment(
        work_item_id, summary, keyword_counts, severity_counts, total_entries_scanned
    )
    return {"status": "success", "id": doc_id}


def store_incident_summary(
    work_item_id: str,
    provider: str,
    summary: str,
    summary_preview: str,
    provider_error: str,
) -> dict:
    """Tool wrapper around save_incident_summary."""
    doc_id = save_incident_summary(
        work_item_id, provider, summary, summary_preview, provider_error
    )
    return {"status": "success", "id": doc_id}


def update_action_transitions(work_item_id: str, transitions: list[dict]) -> dict:
    """Tool wrapper around set_action_transitions."""
    set_action_transitions(work_item_id, transitions)
    return {"status": "success"}


def _get_cluster_owner_email(cluster_name: str) -> str:
    """Helper to retrieve the owner's email address from the mapping Excel in GCS."""
    bucket_name = os.getenv("GCS_OWNER_MAPPING_BUCKET", "lbg-test-pradeep")
    blob_name = os.getenv("GCS_OWNER_MAPPING_BLOB", "owner_mapping.xlsx")

    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)

    if not blob.exists():
        print(f"Owner mapping file gs://{bucket_name}/{blob_name} does not exist.")
        return None

    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        tmp_path = tmp.name
        blob.download_to_filename(tmp_path)

    df = pd.read_excel(tmp_path)
    df.columns = [col.strip().lower() for col in df.columns]

    cluster_col = next((col for col in df.columns if "cluster" in col), None)
    owner_col = next(
        (col for col in df.columns if "owner" in col or "email" in col), None
    )

    if not cluster_col or not owner_col:
        print(
            "Excel columns must contain fields matching 'cluster' and 'owner' or 'email'."
        )
        return None

    row = df[df[cluster_col].astype(str).str.lower() == cluster_name.lower()]
    if not row.empty:
        return str(row.iloc[0][owner_col]).strip()
    return None


def send_incident_email_notification(
    work_item_id: str, cluster_name: str, summary_content: str
) -> dict:
    """Notification Tool: Resolves cluster owner email from GCS, sends SRE summary report via SMTP,
    and records results via persistence helper.
    """
    incident_id = _get_incident_id(work_item_id)
    subject = f"[ALERT] CPU Drift Detected - GKE Cluster: {cluster_name}"

    owner_email = _get_cluster_owner_email(cluster_name)
    if not owner_email:
        err_msg = (
            f"No mapped owner email address found in Excel for cluster: {cluster_name}"
        )
        notification_id = record_notification_result(
            incident_id, work_item_id, "FAILED", [], err_msg, subject
        )
        return {"status": "failed", "error": err_msg}

    smtp_host = os.getenv("SMTP_HOST", "localhost")
    try:
        smtp_port = int(os.getenv("SMTP_PORT", "25"))
    except ValueError:
        smtp_port = 25
    smtp_user = os.getenv("SMTP_USERNAME", "")
    smtp_pass = os.getenv("SMTP_PASSWORD", "")
    smtp_from = os.getenv("SMTP_FROM_EMAIL", "")

    msg = MIMEMultipart()
    msg["From"] = smtp_from
    msg["To"] = owner_email
    msg["Subject"] = subject
    msg.attach(MIMEText(summary_content, "plain"))

    with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
        if smtp_user and smtp_pass:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_from, [owner_email], msg.as_string())

    notification_id = record_notification_result(
        incident_id, work_item_id, "SENT", [owner_email], "", subject
    )
    return {
        "status": "success",
        "recipient": owner_email,
        "notification_id": notification_id,
    }
    """Notification Tool: Resolves cluster owner email from GCS, sends SRE summary report via SMTP,
    and records results via persistence helper.
    """
    incident_id = _get_incident_id(work_item_id)
    notification_id = f"notif_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    subject = f"[ALERT] CPU Drift Detected - GKE Cluster: {cluster_name}"

    owner_email = _get_cluster_owner_email(cluster_name)
    if not owner_email:
        err_msg = (
            f"No mapped owner email address found in Excel for cluster: {cluster_name}"
        )
        record_notification_result(
            notification_id, incident_id, work_item_id, "FAILED", [], err_msg, subject
        )
        return {"status": "failed", "error": err_msg}

    smtp_host = os.getenv("SMTP_HOST", "localhost")
    try:
        smtp_port = int(os.getenv("SMTP_PORT", "25"))
    except ValueError:
        smtp_port = 25
    smtp_user = os.getenv("SMTP_USERNAME", "")
    smtp_pass = os.getenv("SMTP_PASSWORD", "")
    smtp_from = os.getenv("SMTP_FROM_EMAIL", "")

    msg = MIMEMultipart()
    msg["From"] = smtp_from
    msg["To"] = owner_email
    msg["Subject"] = subject
    msg.attach(MIMEText(summary_content, "plain"))

    with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
        if smtp_user and smtp_pass:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_from, [owner_email], msg.as_string())

    record_notification_result(
        notification_id, incident_id, work_item_id, "SENT", [owner_email], "", subject
    )
    return {
        "status": "success",
        "recipient": owner_email,
        "notification_id": notification_id,
    }