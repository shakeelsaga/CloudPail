<p align="center">
  <a href="https://github.com/shakeelsaga/CloudPail">
    <img src="https://cdn.jsdelivr.net/gh/shakeelsaga/CloudPail@main/assets/CloudPail-Banner.png" alt="CloudPail Banner" width="100%">
  </a>
</p>

# CloudPail

[![PyPI Version](https://img.shields.io/pypi/v/cloudpail?color=blue)](https://pypi.org/project/cloudpail/)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![AWS S3](https://img.shields.io/badge/AWS-S3-orange)](https://aws.amazon.com/s3/)
[![Code Style: Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

**The Developer-First Interface for AWS S3 Management.**

CloudPail is a Python-based TUI that simplifies everyday S3 operations by combining the speed of the AWS CLI with the clarity and safety of an interactive interface.

It is designed for developers and cloud engineers who want to manage S3 resources quickly without memorizing verbose commands or relying on slow console workflows.



## Why CloudPail Exists

Managing S3 typically involves a trade-off:

- **AWS Console** → visual but slow and context-breaking  
- **AWS CLI** → fast but error-prone and difficult to memorize  

CloudPail bridges this gap by providing:
- an interactive terminal experience  
- strong safety checks for destructive operations  
- clear visibility into buckets, objects, and actions  

The goal is to reduce manual effort while preventing common operational mistakes.



## Core Capabilities

### Interactive S3 Management
- Browse buckets and objects through a responsive text-based UI  
- Perform uploads, downloads, deletions, and inspections without leaving the terminal  
- Append-only interaction model to preserve session context  

---

### Region-Aware Operations
S3 buckets are region-specific, but many scripts fail due to incorrect endpoint usage.

CloudPail:
- automatically detects the bucket’s region  
- routes requests to the correct regional endpoint  
- avoids common `SignatureDoesNotMatch` errors  

This makes operations reliable across multi-region environments.

---

### Safety-First Deletion Workflow
Destructive actions are guarded by explicit checks.

- Mandatory pre-flight validation using `head_object`  
- Detects non-empty buckets before deletion  
- Supports safe recursive cleanup of objects, versions, and delete markers  

This prevents accidental deletions and silent failures.

---

### Session & Profile Management
- Reads directly from `~/.aws/credentials`  
- Allows instant switching between AWS profiles (dev, staging, prod)  
- Maintains authentication state throughout the session  

Designed for engineers working across multiple environments.

---

### Intelligent Asset Handling
- Automatic MIME-type detection during uploads  
- Recursive directory uploads while preserving structure  
- Presigned URL generation with configurable expiration  
- URLs are copied directly to the clipboard for quick sharing  


## Installation

CloudPail is available on PyPI:

```bash
pip install cloudpail
```

### Upgrade to the latest version:

```bash
pip install --upgrade cloudpail
```


## Configuration

CloudPail uses standard AWS credentials.

If the AWS CLI is already configured, no additional setup is required:

```bash
aws configure
```



## Usage

Launch CloudPail from anywhere in your terminal:

```bash
cloudpail
```

## Navigation

- Arrow keys → navigate lists
- Enter → confirm actions
- Type-to-filter → quickly locate buckets or objects



## Design Decisions

-	TUI over GUI: avoids deployment overhead and keeps workflows terminal-native
-	Append-only interaction: prevents accidental context loss
-	Explicit AWS SDK usage: avoids hidden abstractions over Boto3
-	Safety by default: destructive operations require validation

These choices prioritize reliability, clarity, and operator confidence.



## Tech Stack

-	Python
-	Boto3 (AWS SDK)
-	Rich (terminal rendering)
-	InquirerPy (interactive input)
-	Pyperclip (clipboard integration)



## Status & Roadmap

CloudPail is actively maintained.

Planned improvements include:
-	extended multi-bucket operations
-	configurable safety policies
-	performance optimizations for large object sets



## License

MIT License
© 2025 shakeelsaga