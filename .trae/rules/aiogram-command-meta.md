---
description: Enforce aiogram Telegram command metadata with strict 3-level permission structure
alwaysApply: true
---

# Aiogram Telegram Bot Permission Rules

This Telegram bot supports ONLY three permission levels:

- user
- admin
- owner

No other permission levels are allowed.

---

## Command Directory Structure

All command handlers MUST be placed inside:

- handlers/command/user/
- handlers/command/admin/
- handlers/command/owner/

Do NOT create:

- group/
- mod/
- superadmin/
- staff/
- vip/
- misc/
- utils/

Commands must NOT exist directly under handlers/command/.

---

## Naming Rules

Command filenames must describe functionality only.

Forbidden examples:

- admin_ban.py
- owner_stats.py
- user_upload.py

Correct examples:

- ban.py
- stats.py
- upload.py

Permission is determined ONLY by directory.

---

## Mandatory Metadata

Each command module MUST declare:

COMMAND_META

Example:

```python
COMMAND_META = {
    "name": "ban",
    "alias": "b",
    "usage": "/ban <user>",
    "desc": "封禁用户"
}