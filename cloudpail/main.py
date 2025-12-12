import boto3
import os
import sys
import mimetypes
from botocore.exceptions import ClientError as CE, EndpointConnectionError
from botocore.config import Config
from rich.console import Console, Group
from rich.theme import Theme
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.align import Align
from rich import box
from InquirerPy import inquirer
from InquirerPy.base.control import Choice
try:
    import pyperclip
except ImportError:
    pyperclip = None

# ======= THEME & CONSOLE SETUP =======

# I chose a custom "Matcha" theme here to make the CLI feel professional 
# and distinct from the standard black/white terminal output.
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

# Global variables to maintain state across the application.
# I store the active session here so I don't have to pass the client 
# into every single function argument manually.
active_session = None
active_client = None
current_profile_name = "default"
current_region = "us-east-1"

# ======= UI SUPPORT =======

def print_banner():
    # I used a raw string (r"") here to prevent Python from misinterpreting 
    # the backslashes in the ASCII art as escape characters.
    art_str = r"""
   ________                __ ___        _ __ 
  / ____/ /___  __  ______/ / __ \____ _(_) / 
 / /   / / __ \/ / / / __  / /_/ / __ `/ / /  
/ /___/ / /_/ / /_/ / /_/ / ____/ /_/ / / /   
\____/_/\____/\__,_/\__,_/_/    \__,_/_/_/    
"""
    art = Text(art_str, style="accent")

    subtitle = Text("\nAWS S3 MANAGEMENT INTERFACE  ::  v1.0.5", style="base")

    # This status footer ensures the user always knows their context (Profile/Region)
    # just by glancing at the top of the screen.
    status_content = (
        f"[muted]Profile:[/muted] [bold highlight]{current_profile_name}[/bold highlight]   "
        f"[muted]Region:[/muted] [bold highlight]{current_region}[/bold highlight]"
    )

    # I'm grouping the logo and subtitle to align them perfectly in the center
    # of the panel, regardless of the user's terminal width.
    content = Group(
        Align.center(art),
        Align.center(subtitle)
    )

    console.print(
        Panel(
            content, 
            border_style="border", 
            expand=False, 
            padding=(1, 6),
            subtitle=status_content,
            subtitle_align="center"
        )
    )
    console.print()

def get_context_string():
    """Helper to show active profile in sub-menus header."""
    return f"[dim]({current_profile_name} @ {current_region})[/dim]"

def get_available_profiles():
    """Reads the local ~/.aws/credentials file to find available profiles."""
    return boto3.Session().available_profiles

def init_session(profile_name):
    global active_session, active_client, current_profile_name, current_region
    try:
        active_session = boto3.Session(profile_name=profile_name)
        
        # Defaulting to us-east-1 if the profile doesn't specify a region
        region = active_session.region_name or "us-east-1"
        current_region = region

        # --- CRITICAL FIX ---
        # Boto3 often defaults to the global endpoint, which causes signature errors 
        # in regions like 'ap-south-1'. Here, I am forcing the client to use 
        # the specific regional endpoint to guarantee the cryptographic signature matches.
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
        
        # I run a lightweight 'ping' here (get_caller_identity) to test the connection immediately.
        # This prevents the app from crashing later if the user is offline or has bad keys.
        sts = active_session.client('sts')
        sts.get_caller_identity()
        
        current_profile_name = profile_name
        return True
    except EndpointConnectionError:
        console.print("[error]✖ Network Error: Cannot connect to AWS.[/error]")
        return False
    except CE as e:
        console.print(f"[error]✖ Failed to initialize session: {e}[/error]")
        return False
    except Exception as e:
        console.print(f"[error]✖ CRITICAL: Failed to load profile '{profile_name}': {e}[/error]")
        return False

def format_size(size_bytes):
    """Converts raw bytes into human-readable MB or KB."""
    if size_bytes >= 1048576:
        return f"{size_bytes / 1048576:.2f} MB"
    else:
        return f"{size_bytes / 1024:.2f} KB"

def select_bucket_interactive(client):
    # I wrap this in a spinner because listing buckets can take a few seconds 
    # on slow networks, and I don't want the UI to freeze without feedback.
    with console.status("[accent]Retrieving bucket list...[/]", spinner="aesthetic"):
        buckets = bucket_listing(client)
    
    if not buckets:
        console.print("[warning]⚠ No buckets found in this region.[/warning]")
        return None

    choices = [Choice(b['Name'], name=b['Name']) for b in buckets]
    choices.append(Choice(value=None, name="« Cancel"))

    # InquirerPy provides the interactive arrow-key selection menu
    return inquirer.select(
        message="Select Bucket:",
        choices=choices,
        default=None,
        pointer="⟢"
    ).execute()

def select_object_interactive(client, bucket_name):
    with console.status(f"[accent]Scanning objects in {bucket_name}...[/]", spinner="aesthetic"):
        objects = object_listing(client, bucket_name)

    if not objects:
        console.print("[warning]⚠ Bucket is currently empty.[/warning]")
        return None

    # I'm displaying the file size next to the key name so the user has more context 
    # before selecting an object.
    choices = [Choice(o['Key'], name=f"{o['Key']}  ({format_size(o['Size'])})") for o in objects[:50]]
    
    # Truncating the list at 50 items to keep the terminal responsive. 
    # A production upgrade would be to implement pagination here.
    if len(objects) > 50:
        choices.append(Choice(value=None, name="... (List truncated for performance)"))
    
    choices.append(Choice(value=None, name="« Cancel"))

    return inquirer.select(
        message="Select Object:",
        choices=choices,
        default=None,
        pointer="⟢"
    ).execute()

# ======= BACKEND: BUCKET OPS =======

def bucket_listing(client):
    try:
        response = client.list_buckets()
        return response.get("Buckets", [])
    # Catching EndpointConnectionError specifically to handle internet drops gracefully
    except EndpointConnectionError:
        console.print("[error]✖ Network Error: Cannot connect to AWS.[/error]")
        return []
    except CE as e:
        console.print(f"[error]✖ Failed to list buckets: {e}[/error]")
        return []

def bucket_creation(client, bucket_name, region):
    if not region: region = "us-east-1"
    try:
        # AWS requires a LocationConstraint for all regions EXCEPT us-east-1.
        # This logic handles that quirk.
        if region == "us-east-1":
            client.create_bucket(Bucket=bucket_name)
        else:
            client.create_bucket(Bucket=bucket_name, CreateBucketConfiguration={"LocationConstraint": region})
        return True
    except EndpointConnectionError:
        console.print("[error]✖ Network Error: Cannot connect to AWS.[/error]")
        return False
    except CE as e:
        console.print(f"[error]✖ Creation Failed: {e}[/error]")
        return False

def is_bucket_empty(client, bucket_name):
    try:
        # A simple 'list_objects' isn't enough because a bucket might contain 
        # hidden DeleteMarkers or Versions. This check ensures it's TRULY empty.
        response = client.list_object_versions(Bucket=bucket_name, MaxKeys=1)
        return not ("Versions" in response or "DeleteMarkers" in response)
    except EndpointConnectionError:
        console.print("[error]✖ Network Error: Cannot connect to AWS.[/error]")
        return False
    except CE as e:
        console.print(f"[error]✖ Could not determine if bucket is empty: {e}[/error]")
        return False

def bucket_emptying(client, bucket_name):
    console.print(f"[muted]» Preparing to clear '{bucket_name}'...[/muted]")
    try:
        with console.status("[accent]Removing objects and versions...[/]", spinner="aesthetic"):
            paginator = client.get_paginator("list_object_versions")
            # We iterate through every page of the bucket to find all versions and delete markers
            for page in paginator.paginate(Bucket=bucket_name):
                to_delete = []
                for v in page.get("Versions", []):
                    to_delete.append({"Key": v["Key"], "VersionId": v["VersionId"]})
                for dm in page.get("DeleteMarkers", []):
                    to_delete.append({"Key": dm["Key"], "VersionId": dm["VersionId"]})
                
                # Batch delete is much faster than deleting one by one
                if to_delete:
                    client.delete_objects(Bucket=bucket_name, Delete={"Objects": to_delete})
        return True
    except EndpointConnectionError:
        console.print("[error]✖ Network Error: Cannot connect to AWS.[/error]")
        return False
    except CE as e:
        console.print(f"[error]✖ Operation Failed: {e}[/error]")
        return False

def bucket_deletion(client, bucket_name):
    try:
        # Step 1: Check if the bucket is empty. AWS refuses to delete non-empty buckets.
        with console.status("[accent]Verifying bucket status...[/]", spinner="aesthetic"):
            empty = is_bucket_empty(client, bucket_name)

        # Step 2: If not empty, I offer to recursively empty it for the user.
        if not empty:
            console.print(f"[warning]⚠ Bucket '{bucket_name}' is not empty.[/warning]")
            confirm = inquirer.confirm(
                message="Recursively delete all contents and the bucket?", 
                default=False
            ).execute()
            
            if not confirm:
                return False
            
            if not bucket_emptying(client, bucket_name):
                return False

        # Step 3: Perform the actual deletion
        with console.status("[accent]Deleting bucket...[/]", spinner="aesthetic"):
            client.delete_bucket(Bucket=bucket_name)
        
        console.print(f"[success]✔ Bucket '{bucket_name}' successfully deleted.[/success]")
        return True
    except EndpointConnectionError:
        console.print("[error]✖ Network Error: Cannot connect to AWS.[/error]")
        return False
    except CE as e:
        console.print(f"[error]✖ Error: {e}[/error]")
        return False

# ======= BACKEND: OBJECT OPS =======

def check_object_exists(client, bucket_name, key):
    """Performs a lightweight HEAD request to verify existence before operations."""
    try:
        client.head_object(Bucket=bucket_name, Key=key)
        return True
    except EndpointConnectionError:
        console.print("[error]✖ Network Error: Cannot connect to AWS.[/error]")
        return None
    except CE:
        return False

def object_listing(client, bucket_name):
    try:
        paginator = client.get_paginator("list_objects_v2")
        results = []
        for page in paginator.paginate(Bucket=bucket_name):
            results.extend(page.get("Contents", []))
        return results
    except EndpointConnectionError:
        console.print("[error]✖ Network Error: Cannot connect to AWS.[/error]")
        return []
    except CE as e:
        console.print(f"[error]✖ Failed to list objects: {e}[/error]")
        return []

def object_uploading(client, path, bucket_name, key):
    if not os.path.exists(path):
        console.print(f"[error]✖ File path invalid: {path}[/error]")
        return False
    
    # I auto-detect the MIME type here so that when users open the link in a browser, 
    # it renders correctly (e.g., image shows up) instead of just downloading.
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
        console.print(f"[success]✔ Upload Complete: {key}[/success]")
        return True
    except EndpointConnectionError:
        console.print("[error]✖ Network Error: Cannot connect to AWS.[/error]")
        return False
    except CE as e:
        console.print(f"[error]✖ Upload Failed: {e}[/error]")
        return False

def object_folder_uploading(client, bucket_name, folder_path):
    console.print(f"[accent]» Initiating batch upload from: {folder_path}[/accent]")
    count = 0
    # Recursive walk through the directory
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            local = os.path.join(root, file)
            relative = os.path.relpath(local, folder_path)
            # Converting Windows backslashes to S3 forward slashes
            key = relative.replace("\\", "/")
            
            # DOOM LOOP CHECK: If one upload fails (e.g. internet lost), 
            # I stop the whole batch immediately to avoid spamming errors.
            if not object_uploading(client, local, bucket_name, key):
                console.print("[warning]⚠ Batch upload interrupted due to error.[/warning]")
                return
            count += 1
    console.print(f"\n[success]✔ Batch Operation Complete. {count} files processed.[/success]")

def object_downloading(client, bucket_name, key):
    try:
        dl_name = "downloaded_" + os.path.basename(key)
        with console.status(f"[accent]Downloading {key}...[/]", spinner="aesthetic"):
            client.download_file(Bucket=bucket_name, Key=key, Filename=dl_name)
        console.print(f"[success]✔ Download Saved: {dl_name}[/success]")
    except EndpointConnectionError:
        console.print("[error]✖ Network Error: Cannot connect to AWS.[/error]")
    except CE as e:
        console.print(f"[error]✖ Download Failed: {e}[/error]")

def object_deletion(client, bucket_name, key):
    # Verification Step: I check if the object exists first to avoid 
    # giving the user false positive "Success" messages.
    with console.status("[accent]Verifying object...[/]", spinner="aesthetic"):
        exists = check_object_exists(client, bucket_name, key)

    if exists is None:
        return False 
    
    if not exists:
        console.print(f"[error]✖ Error: Object '{key}' could not be found.[/error]")
        return False

    try:
        with console.status(f"[accent]Removing {key}...[/]", spinner="aesthetic"):
            client.delete_object(Bucket=bucket_name, Key=key)
        console.print(f"[success]✔ Object '{key}' successfully deleted.[/success]")
        return True
    except EndpointConnectionError:
        console.print("[error]✖ Network Error: Cannot connect to AWS.[/error]")
        return False
    except CE as e:
        console.print(f"[error]✖ Deletion Failed: {e}[/error]")
        return False

def object_meta_data(client, bucket_name, key):
    try:
        response = client.head_object(Bucket=bucket_name, Key=key)
        
        console.print()
        # Using a Rounded Table to display metadata cleanly
        table = Table(title="Object Properties", border_style="border", box=box.ROUNDED)
        table.add_column("Property", style="accent", justify="right")
        table.add_column("Value", style="base")
        
        table.add_row("Key Name", key)
        table.add_row("Size", format_size(response['ContentLength']))
        table.add_row("MIME Type", response['ContentType'])
        table.add_row("Last Modified", str(response['LastModified']))
        
        console.print(table)
    except EndpointConnectionError:
        console.print("[error]✖ Network Error: Cannot connect to AWS.[/error]")
    except CE:
        console.print("[error]✖ Unable to retrieve metadata.[/error]")

def object_pre_sign(client, bucket_name, key):
    try:
        url = client.generate_presigned_url(
            ClientMethod="get_object",
            Params={"Bucket": bucket_name, "Key": key},
            ExpiresIn=3600,
        )
        
        console.print("\n[success]✔ Secure Link Generated (Expires in 1 Hour):[/success]")
        console.print(f"[link={url}]{url}[/link]", soft_wrap=True) 
        
        # This is a huge convenience feature: Auto-copy to clipboard
        if pyperclip:
            pyperclip.copy(url)
            console.print("[accent](URL copied to clipboard)[/accent]")
        else:
            console.print("[muted](Install 'pyperclip' to enable auto-copy)[/muted]")
            
    except CE as e:
        console.print(f"[error]✖ Error: {e}[/error]")

# ======= MENUS =======

def bucket_operation_menu():
    while True:
        console.print()
        # I added context strings to the headers so the user always knows 
        # which profile they are using, even inside deep sub-menus.
        console.rule(f"[bold accent]Bucket Management[/] {get_context_string()}", style="border")
        op = inquirer.select(
            message="Select Action:",
            choices=[
                Choice("create", name="Create New Bucket"),
                Choice("list", name="List All Buckets"),
                Choice("delete", name="Delete Bucket"),
                Choice("menu", name="« Return to Main Menu"),
            ],
            default="list",
            pointer="⟢"
        ).execute()

        if op == "menu": break

        if op == "create":
            name = inquirer.text(message="Bucket Name:").execute()
            region = inquirer.text(message="Region (default: us-east-1):").execute()
            with console.status("[accent]Provisioning...[/]", spinner="aesthetic"):
                if bucket_creation(active_client, name, region):
                    console.print(f"[success]✔ Bucket '{name}' provisioned successfully.[/success]")

        elif op == "list":
            with console.status("[accent]Querying Region...[/]", spinner="aesthetic"):
                buckets = bucket_listing(active_client)
            if buckets:
                console.print()
                t = Table(title="Active Buckets", border_style="border", box=box.ROUNDED)
                t.add_column("Bucket Name", style="highlight")
                t.add_column("Creation Date", style="muted")
                for b in buckets: t.add_row(b['Name'], str(b['CreationDate'].strftime("%Y-%m-%d %H:%M")))
                console.print(t)
            else:
                console.print("[muted]No buckets found in this region.[/muted]")

        elif op == "delete":
            target = select_bucket_interactive(active_client)
            if target: bucket_deletion(active_client, target)

def object_operation_menu():
    console.print("[muted]Select target bucket:[/muted]")
    bucket = select_bucket_interactive(active_client)
    if not bucket: return

    while True:
        console.print()
        console.rule(f"[bold accent]Object Management: {bucket}[/] {get_context_string()}", style="border")
        op = inquirer.select(
            message="Select Action:",
            choices=[
                Choice("list", name="List Objects"),
                Choice("upload", name="Upload File"),
                Choice("folder", name="Upload Folder (Recursive)"),
                Choice("download", name="Download Object"),
                Choice("meta", name="Inspect Metadata"),
                Choice("presign", name="Generate Presigned URL"),
                Choice("delete", name="Delete Object"),
                Choice("menu", name="« Return to Main Menu"),
            ],
            default="list",
            pointer="⟢"
        ).execute()

        if op == "menu": break

        if op == "list":
            with console.status("[accent]Indexing...[/]", spinner="aesthetic"):
                objs = object_listing(active_client, bucket)
            if objs:
                console.print()
                t = Table(border_style="border", box=box.ROUNDED, title=f"Contents of {bucket}")
                t.add_column("Object Key", style="base")
                t.add_column("Size", style="muted", justify="right")
                for o in objs: t.add_row(o['Key'], format_size(o['Size']))
                console.print(t)
            else:
                console.print("[warning]⚠ Bucket is currently empty.[/warning]")

        elif op == "upload":
            path = inquirer.filepath(message="Local File Path:").execute()
            if path:
                key = inquirer.text(message="Destination Key:", default=os.path.basename(path)).execute()
                object_uploading(active_client, path, bucket, key)

        elif op == "folder":
            path = inquirer.filepath(message="Folder Path:", only_directories=True).execute()
            if path: object_folder_uploading(active_client, bucket, path)

        elif op in ["download", "meta", "presign", "delete"]:
            target = select_object_interactive(active_client, bucket)
            if target:
                if op == "download": object_downloading(active_client, bucket, target)
                elif op == "meta": object_meta_data(active_client, bucket, target)
                elif op == "presign": object_pre_sign(active_client, bucket, target)
                elif op == "delete": object_deletion(active_client, bucket, target)

def main():
    # Force profile selection at start to ensure variables are set before banner prints
    profiles = get_available_profiles()
    if not profiles:
        console.print("[error]✖ No AWS configuration found. Please run 'aws configure'.[/error]")
        sys.exit(1)
    
    # Initialize first profile silently, then print banner
    init_session(profiles[0])
    print_banner()

    # The main loop keeps the application alive until the user explicitly quits.
    while True:
        console.print()
        console.rule(f"[bold accent]Main Menu[/] {get_context_string()}", style="border")
        op = inquirer.select(
            message="System Operation:",
            choices=[
                Choice("bucket", name="Bucket Management"),
                Choice("object", name="Object Management"),
                Choice("profile", name="Switch AWS Profile"),
                Choice("quit", name="Exit Application"),
            ],
            pointer="⟢"
        ).execute()

        if op == "bucket": bucket_operation_menu()
        elif op == "object": object_operation_menu()
        elif op == "profile":
            p = inquirer.select(message="Select AWS Profile:", choices=profiles, pointer="⟢").execute()
            if init_session(p):
                # Repaint banner to reflect new profile prominently
                print_banner()
        else:
            console.print("[warning]Session terminated. Exiting application.[/warning]")
            sys.exit(0)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[warning]Operation cancelled by user.[/warning]")
        sys.exit(0)