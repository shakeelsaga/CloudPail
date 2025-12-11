import boto3
import os
import sys
import mimetypes
from botocore.exceptions import ClientError as CE
from botocore.config import Config
from rich.console import Console
from rich.theme import Theme
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from InquirerPy import inquirer
from InquirerPy.base.control import Choice
try:
    import pyperclip
except ImportError:
    pyperclip = None

# ======= THEME & CONSOLE SETUP =======

theme_matcha = Theme(
    {
        "base": "#f0f0f0",      # Cream
        "accent": "#7daea3",    # Matcha Green
        "highlight": "#89b482", # Leaf Green
        "success": "#a9b665",   # Olive Green
        "warning": "#d3869b",   # Muted Pink
        "error": "#ea6962",     # Earthy Red
        "muted": "#928374",     # Brownish Grey
        "border": "#7daea3",    # Matcha Borders
    }
)

console = Console(theme=theme_matcha)
active_session = None
active_client = None
current_profile_name = "default"

# ======= UI SUPPORT =======

def splash():
    logo = r"""
    [accent]
       ________                _______       _ __ 
      / ____/ /___  __  ______/ /  __ \___ _(_) / 
     / /   / / __ \/ / / / __  / /_/ / __ `/ / /  
    / /___/ / /_/ / /_/ / /_/ / ____/ /_/ / / /   
    \____/_/\____/\__,_/\__,_/_/    \__,_/_/_/    
    [/accent]
    [base]   CloudPail CLI  ::  v1.0[/base]
    """
    console.print(Panel(logo, border_style="border", expand=False))
    console.print(f"[muted]   Logged in as: [bold highlight]{current_profile_name}[/][/muted]\n")

def get_available_profiles():
    return boto3.Session().available_profiles

from botocore.config import Config # Import this at top

def init_session(profile_name):
    global active_session, active_client, current_profile_name
    try:
        active_session = boto3.Session(profile_name=profile_name)
        
        region = active_session.region_name or "us-east-1"

        if region == "us-east-1":
            endpoint = "https://s3.us-east-1.amazonaws.com"
        else:
            endpoint = f"https://s3.{region}.amazonaws.com"

        active_client = active_session.client(
            's3', 
            region_name=region,
            endpoint_url=endpoint,
            config=Config(signature_version='s3v4')
        )
        
        current_profile_name = profile_name
        return True
    except Exception as e:
        console.print(f"[error]Failed to load profile '{profile_name}': {e}[/error]")
        return False

def select_bucket_interactive(client):
    with console.status("[accent]Fetching buckets...[/]", spinner="aesthetic"):
        buckets = bucket_listing(client)
    
    if not buckets:
        console.print("[warning]No buckets found![/warning]")
        return None

    choices = [Choice(b['Name'], name=b['Name']) for b in buckets]
    choices.append(Choice(value=None, name="❌ Cancel"))

    return inquirer.select(
        message="Select a Bucket:",
        choices=choices,
        default=None,
        pointer="⟢"
    ).execute()

def select_object_interactive(client, bucket_name):
    with console.status(f"[accent]Fetching objects from {bucket_name}...[/]", spinner="aesthetic"):
        objects = object_listing(client, bucket_name)

    if not objects:
        console.print("[warning]Bucket is empty![/warning]")
        return None

    choices = [Choice(o['Key'], name=f"{o['Key']} ({o['Size']/1024:.1f} KB)") for o in objects[:50]]
    if len(objects) > 50:
        choices.append(Choice(value=None, name="... (List truncated, use search logic for more)"))
    
    choices.append(Choice(value=None, name="❌ Cancel"))

    return inquirer.select(
        message="Select an Object:",
        choices=choices,
        default=None,
        pointer="⟢"
    ).execute()

# ======= BACKEND: BUCKET OPS =======

def bucket_listing(client):
    try:
        response = client.list_buckets()
        return response.get("Buckets", [])
    except CE as e:
        console.print(f"[error]Error listing buckets: {e}[/error]")
        return []

def bucket_creation(client, bucket_name, region):
    if not region: region = "us-east-1"
    try:
        if region == "us-east-1":
            client.create_bucket(Bucket=bucket_name)
        else:
            client.create_bucket(Bucket=bucket_name, CreateBucketConfiguration={"LocationConstraint": region})
        return True
    except CE as e:
        console.print(f"[error]AWS Error: {e}[/error]")
        return False

def is_bucket_empty(client, bucket_name):
    try:
        response = client.list_object_versions(Bucket=bucket_name, MaxKeys=1)
        return not ("Versions" in response or "DeleteMarkers" in response)
    except CE:
        return False

def bucket_emptying(client, bucket_name):
    console.print(f"[muted]🧹 Emptying '{bucket_name}'...[/muted]")
    try:
        with console.status("[accent]Purging objects...[/]", spinner="aesthetic"):
            paginator = client.get_paginator("list_object_versions")
            for page in paginator.paginate(Bucket=bucket_name):
                to_delete = []
                for v in page.get("Versions", []):
                    to_delete.append({"Key": v["Key"], "VersionId": v["VersionId"]})
                for dm in page.get("DeleteMarkers", []):
                    to_delete.append({"Key": dm["Key"], "VersionId": dm["VersionId"]})
                
                if to_delete:
                    client.delete_objects(Bucket=bucket_name, Delete={"Objects": to_delete})
        return True
    except CE as e:
        console.print(f"[error]Failed to empty bucket: {e}[/error]")
        return False

def bucket_deletion(client, bucket_name):
    try:
        # 1. Check content (Spinning)
        with console.status("[accent]Checking contents...[/]", spinner="aesthetic"):
            empty = is_bucket_empty(client, bucket_name)

        # 2. Interaction (No Spinner)
        if not empty:
            console.print(f"[warning]⚠️  Bucket '{bucket_name}' is not empty![/warning]")
            if not inquirer.confirm(message="Force delete (nuke contents)?", default=False).execute():
                return False
            if not bucket_emptying(client, bucket_name):
                return False

        # 3. Delete (Spinning)
        with console.status("[accent]Deleting bucket...[/]", spinner="aesthetic"):
            client.delete_bucket(Bucket=bucket_name)
        
        console.print(f"[success]✔ Bucket '{bucket_name}' deleted.[/success]")
        return True
    except CE as e:
        console.print(f"[error]Error: {e}[/error]")
        return False

# ======= BACKEND: OBJECT OPS =======

def check_object_exists(client, bucket_name, key):
    """The truth-teller function."""
    try:
        client.head_object(Bucket=bucket_name, Key=key)
        return True
    except CE:
        return False

def object_listing(client, bucket_name):
    try:
        paginator = client.get_paginator("list_objects_v2")
        results = []
        for page in paginator.paginate(Bucket=bucket_name):
            results.extend(page.get("Contents", []))
        return results
    except CE:
        return []

def object_uploading(client, path, bucket_name, key):
    # SPINNER MOVED INSIDE HERE as requested
    if not os.path.exists(path):
        console.print(f"[error]File not found: {path}[/error]")
        return False
    
    mime_type, _ = mimetypes.guess_type(path)
    if not mime_type: mime_type = 'binary/octet-stream'

    try:
        with console.status(f"[accent]Uploading {key}...[/]", spinner="aesthetic"):
            client.upload_file(
                Filename=path, 
                Bucket=bucket_name, 
                Key=key,
                ExtraArgs={'ContentType': mime_type}
            )
        console.print(f"[success]⬆️  Uploaded: {key}[/success]")
        return True
    except CE as e:
        console.print(f"[error]Upload failed: {e}[/error]")
        return False

def object_folder_uploading(client, bucket_name, folder_path):
    console.print(f"[accent]🚀 Starting batch upload from: {folder_path}[/accent]")
    count = 0
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            local = os.path.join(root, file)
            relative = os.path.relpath(local, folder_path)
            key = relative.replace("\\", "/")
            # Reuse single upload function so we get the spinner per file!
            object_uploading(client, local, bucket_name, key)
            count += 1
    console.print(f"\n[success]✔ Batch complete. {count} files processed.[/success]")

def object_downloading(client, bucket_name, key):
    try:
        dl_name = "downloaded_" + os.path.basename(key)
        with console.status(f"[accent]Downloading {key}...[/]", spinner="aesthetic"):
            client.download_file(Bucket=bucket_name, Key=key, Filename=dl_name)
        console.print(f"[success]⬇️  Saved to: {dl_name}[/success]")
    except CE as e:
        console.print(f"[error]Download failed: {e}[/error]")

def object_deletion(client, bucket_name, key):
    # 1. TRUTH CHECK
    with console.status("[accent]Verifying object...[/]", spinner="aesthetic"):
        exists = check_object_exists(client, bucket_name, key)
    
    if not exists:
        console.print(f"[error]❌ Error: Object '{key}' does not exist in this bucket![/error]")
        return False

    # 2. DELETE
    try:
        with console.status(f"[accent]Deleting {key}...[/]", spinner="aesthetic"):
            client.delete_object(Bucket=bucket_name, Key=key)
        console.print(f"[success]🗑️  Object '{key}' deleted.[/success]")
        return True
    except CE as e:
        console.print(f"[error]Delete failed: {e}[/error]")
        return False

def object_meta_data(client, bucket_name, key):
    try:
        response = client.head_object(Bucket=bucket_name, Key=key)
        
        # Clean Table Output
        table = Table(title=f"Metadata: {key}", border_style="border")
        table.add_column("Property", style="accent")
        table.add_column("Value", style="base")
        
        table.add_row("Size", f"{response['ContentLength']} bytes")
        table.add_row("Type", response['ContentType'])
        table.add_row("Last Modified", str(response['LastModified']))
        console.print(table)
    except CE:
        console.print("[error]❌ Could not fetch metadata.[/error]")



def object_pre_sign(client, bucket_name, key):
    try:
        url = client.generate_presigned_url(
            ClientMethod="get_object",
            Params={"Bucket": bucket_name, "Key": key},
            ExpiresIn=3600,
        )
        
        console.print("\n[success]✔ Presigned URL Generated (Valid for 1 Hour):[/success]")
        
        console.print(f"[link={url}]{url}[/link]", soft_wrap=True) 
        
        if pyperclip:
            pyperclip.copy(url)
            console.print("[accent](Link has been copied to your clipboard!)[/accent]")
        else:
            console.print("[muted](Tip: Install 'pyperclip' to auto-copy this link)[/muted]")
            
    except CE as e:
        console.print(f"[error]Error: {e}[/error]")

# ======= MENUS =======

def bucket_operation_menu():
    while True:
        console.rule("[bold accent]Bucket Operations[/]")
        op = inquirer.select(
            message="Choose Action:",
            choices=[
                Choice("create", name="Create Bucket"),
                Choice("list", name="List Buckets"),
                Choice("delete", name="Delete Bucket"),
                Choice("menu", name="⬅ Back"),
            ],
            default="list",
            pointer="⟢"
        ).execute()

        if op == "menu": break

        if op == "create":
            name = inquirer.text(message="Bucket Name:").execute()
            region = inquirer.text(message="Region (default: us-east-1):").execute()
            # Spinner is inside the function for region check, but create is fast.
            # We can wrap it here since no input inside.
            with console.status("[accent]Creating...[/]", spinner="aesthetic"):
                if bucket_creation(active_client, name, region):
                    console.print(f"[success]✔ Bucket '{name}' created.[/success]")

        elif op == "list":
            with console.status("[accent]Fetching...[/]", spinner="aesthetic"):
                buckets = bucket_listing(active_client)
            if buckets:
                t = Table(title="Your Buckets", border_style="border")
                t.add_column("Name", style="highlight")
                t.add_column("Created", style="muted")
                for b in buckets: t.add_row(b['Name'], str(b['CreationDate'].strftime("%Y-%m-%d")))
                console.print(t)
            else:
                console.print("[muted]No buckets found.[/muted]")

        elif op == "delete":
            target = select_bucket_interactive(active_client)
            if target: bucket_deletion(active_client, target)

def object_operation_menu():
    console.print("[muted]Select a bucket to work on:[/muted]")
    bucket = select_bucket_interactive(active_client)
    if not bucket: return

    while True:
        console.rule(f"[bold accent]Object Ops: {bucket}[/]")
        op = inquirer.select(
            message="Choose Action:",
            choices=[
                Choice("list", name="List All Objects"),
                Choice("upload", name="Upload File"),
                Choice("folder", name="Upload Folder"),
                Choice("download", name="Download Object"),
                Choice("meta", name="View Metadata"),
                Choice("presign", name="Generate Presigned URL"),
                Choice("delete", name="Delete Object"),
                Choice("menu", name="⬅ Back"),
            ],
            default="list",
            pointer="⟢"
        ).execute()

        if op == "menu": break

        if op == "list":
            with console.status("[accent]Listing...[/]", spinner="aesthetic"):
                objs = object_listing(active_client, bucket)
            if objs:
                t = Table(border_style="border")
                t.add_column("Key", style="base")
                t.add_column("Size", style="muted")
                for o in objs: t.add_row(o['Key'], f"{o['Size']/1024:.2f} KB")
                console.print(t)
            else:
                console.print("[warning]Bucket is empty.[/warning]")

        elif op == "upload":
            path = inquirer.filepath(message="File Path:").execute()
            if path:
                key = inquirer.text(message="S3 Key:", default=os.path.basename(path)).execute()
                object_uploading(active_client, path, bucket, key)

        elif op == "folder":
            path = inquirer.filepath(message="Folder Path:", only_directories=True).execute()
            if path: object_folder_uploading(active_client, bucket, path)

        # For these operations, we use the SELECTOR instead of typing
        elif op in ["download", "meta", "presign", "delete"]:
            target = select_object_interactive(active_client, bucket)
            if target:
                if op == "download": object_downloading(active_client, bucket, target)
                elif op == "meta": object_meta_data(active_client, bucket, target)
                elif op == "presign": object_pre_sign(active_client, bucket, target)
                elif op == "delete": object_deletion(active_client, bucket, target)

def main():
    splash()

    profiles = get_available_profiles()
    if not profiles:
        console.print("[error]No AWS credentials found![/error]")
        sys.exit(1)
    
    init_session(profiles[0]) # Default to first profile

    while True:
        op = inquirer.select(
            message="Main Menu:",
            choices=[
                Choice("bucket", name="Bucket Operations"),
                Choice("object", name="Object Operations"),
                Choice("profile", name="Switch Profile"),
                Choice("quit", name="Quit"),
            ],
            pointer="⟢"
        ).execute()

        if op == "bucket": bucket_operation_menu()
        elif op == "object": object_operation_menu()
        elif op == "profile":
            p = inquirer.select(message="Select Profile:", choices=profiles, pointer="⟢").execute()
            init_session(p)
        else:
            console.print("[warning]Bye! 👋[/warning]")
            sys.exit(0)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)