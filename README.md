# ☁️ CloudPail

> **The Developer-First CLI for AWS S3.**
> Stop fighting with the AWS Console. Manage buckets and objects with speed and style.

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![AWS](https://img.shields.io/badge/AWS-S3-orange)

## Features
* **Interactive UI:** Navigate buckets and objects using arrow keys. No more typing long names.
* **Profile Switcher:** Instantly toggle between `dev`, `prod`, and `test` AWS accounts.
* **Safety First:** "Visual Deletion" checks prevent you from deleting the wrong files.
* **Smart Uploads:** Auto-detects file types (MIME) and supports recursive folder uploads.
* **Presigned URLs:** Generate shareable links in one click (auto-copied to clipboard).
* **Region Aware:** Automatically handles S3 Endpoint URLs to prevent Signature errors.

## 📦 Installation

```bash
# 1. Clone the repo
git clone [https://github.com/yourusername/CloudPail.git](https://github.com/yourusername/CloudPail.git)

# 2. Go to directory
cd CloudPail

# 3. Install (Editable Mode)
pip install -e .