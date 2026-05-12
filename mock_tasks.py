import time
from tarsq.core.decorator import task, schedule


# @schedule(name="send_email", cron="every minute")  # Cron Jobs
@task(
    name="send_email",
    max_retries=1,
    timeout=2,
)
async def send_email(ctx, payload):
    print(f"This is the context: {ctx}")
    email = payload["email"]
    time.sleep(4)
    print(f"  -> email sent: to: {email}")


@task(name="resize_image")
def resize_image(ctx, url=None, **kwargs):
    time.sleep(3)
    print(f"  -> image resized: {url}")


@task(name="generate_report")
def generate_report(ctx, report_type=None, **kwargs):
    time.sleep(2)
    print(f"  -> report generated: {report_type}")


@task(name="send_notification")
def send_notification(ctx, user_id=None, message=None, **kwargs):
    time.sleep(0.5)
    print(f"  -> notification sent to user {user_id}: {message}")


@task(name="process_payment")
def process_payment(ctx, amount=None, currency="USD", **kwargs):
    time.sleep(2)
    print(f"  -> payment processed: {amount} {currency}")


@task(name="compress_video")
def compress_video(ctx, video_id=None, **kwargs):
    time.sleep(20)
    print(f"  -> video compressed: {video_id}")


@task(name="sync_database")
def sync_database(ctx, table=None, **kwargs):
    time.sleep(1.5)
    print(f"  -> database synced: {table}")


@task(name="export_csv")
def export_csv(ctx, dataset=None, **kwargs):
    time.sleep(0.8)
    print(f"  -> csv exported: {dataset}")


@task(name="send_sms")
def send_sms(ctx, phone=None, message=None, **kwargs):
    time.sleep(0.3)
    print(f"  -> sms sent to {phone}: {message}")


@task("backup_files")
def backup_files(ctx, path=None, **kwargs):
    time.sleep(2.5)
    print(f"  -> files backed up: {path}")
