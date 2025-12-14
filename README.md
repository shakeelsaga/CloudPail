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

CloudPail is a terminal-based utility designed to bridge the gap between the complex, syntax-heavy AWS CLI and the latency-prone AWS Console. It provides a robust Text User Interface (TUI) for managing cloud storage resources with speed, precision, and operational safety.

---

## Project Overview

Managing S3 resources often requires a trade-off between speed and usability. The AWS Console offers visual feedback but suffers from slow load times and context switching. The AWS CLI offers speed but requires memorizing verbose commands and lacks safeguards against user error.

CloudPail resolves this by offering an interactive shell that adheres to the **"Append-Only"** design philosophy, preserving session context while providing immediate visual feedback for all operations.

## Core Capabilities

### 1. Region-Aware Architecture
Standard Boto3 implementations often default to global endpoints, causing `SignatureDoesNotMatch` errors when interacting with buckets in specific regions (e.g., `eu-north-1`). CloudPail automatically detects the bucket's region and routes requests to the correct regional endpoint, ensuring cryptographic signature compliance across all AWS zones.

### 2. Operational Safety Protocols
* **Verification:** Implements mandatory `head_object` pre-flight checks before deletion to prevent "false positives" on non-existent resources.
* **Recursive Cleanup:** Includes logic to detect non-empty buckets and offers a recursive deletion workflow to remove all objects, delete markers, and versions before removing the bucket itself.

### 3. Session Management
* **Dynamic Profile Switching:** Reads directly from `~/.aws/credentials` to allow instant context switching between environments (e.g., Development, Staging, Production) without restarting the shell.
* **Session Persistence:** Maintains authentication state globally across the application lifecycle.

### 4. Intelligent Asset Management
* **MIME-Type Detection:** Automatically identifies file types during upload to set accurate `Content-Type` headers, ensuring assets render correctly in web browsers.
* **Recursive Folder Uploads:** Supports batch uploading of directory structures while maintaining the hierarchy within the S3 bucket.
* **Presigned URL Generation:** Generates secure, time-limited access links (1-hour expiration) and automatically copies them to the system clipboard for immediate sharing.


## Installation

CloudPail is available on the Python Package Index (PyPI). You can install it directly using `pip`:

```bash
pip install cloudpail
```

To upgrade to the latest version, run:

```bash
pip install --upgrade cloudpail
```


## Configuration

CloudPail utilizes your standard AWS credentials.

  * If you have already configured the AWS CLI, no further setup is required.
  * If you are setting up this machine for the first time, run: `aws configure`

## Usage

Once installed, the application is available system-wide using the `cloudpail` command:

```bash
cloudpail
```

## Navigation

The interface uses standard keyboard controls for efficient operation:

  * **Arrow Keys:** Navigate through bucket and object lists.
  * **Enter:** Confirm selection or execute the chosen action.
  * **Type-to-Filter:** Rapidly filter long lists by typing the resource name directly into the menu.

## System Architecture

CloudPail is built upon a modern Python stack designed for reliability and performance:

  * **Boto3:** Handles low-level AWS SDK interactions, authentication, and session management.
  * **Rich:** Renders high-performance tables, status indicators, and formatted terminal output.
  * **InquirerPy:** Manages interactive user input, validation, and menu navigation.
  * **Pyperclip:** Provides cross-platform clipboard integration for copying presigned URLs.

## Contributing

CloudPail is an open-source project, and contributions are always welcome\! Whether you're interested in fixing bugs, adding new features, or improving documentation, your help is appreciated.

If you'd like to contribute, please feel free to:

  - Fork the repository and submit a pull request.
  - Open an issue to report bugs or suggest improvements.

## License

This project is distributed under the MIT License. See `LICENSE` for more information.

Copyright (c) 2025 shakeelsaga.

