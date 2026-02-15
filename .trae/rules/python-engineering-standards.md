---
description: Enforce Python engineering standards, reuse logic, maintain clean architecture and Chinese commit messages
alwaysApply: true
---

# Python Engineering Standards for Telegram Bot

This project must follow clean architecture and maintainable engineering practices.

---

## Commit Message Rules

All git commit messages MUST:

- Be written in Chinese
- Clearly describe the purpose of the change
- Follow this format:

<类型>: <简要说明>

Examples:

- 新增: 管理员封禁命令
- 修复: 用户注册逻辑异常
- 优化: 命令扫描性能
- 重构: 权限校验逻辑复用
- 移除: 无用的重复函数

Do NOT use English commit messages.
Do NOT use meaningless messages such as:

- update
- fix bug
- change
- test

---

## Code Reuse

When modifying or adding functionality:

- Check existing services, utils, handlers first
- Reuse existing logic if similar functionality exists
- DO NOT duplicate validation or permission logic
- Extract shared logic into services or utils

Repeated logic MUST be refactored into reusable functions.

---

## Architecture Rules

Follow separation of concerns:

- handlers: Telegram interaction only
- services: business logic
- repositories: database access
- utils: pure helper functions

Handlers MUST NOT contain business logic.

---

## Code Quality

All generated or modified code MUST be:

- Concise
- Efficient
- Elegant
- Readable
- Extensible
- Modular

Avoid:

- Long functions (>50 lines)
- Nested condition chains
- Hardcoded values
- Duplicate database queries
- Repeated permission checks

---

## File Structure Planning

When adding new features:

- Place logic into correct layer (handler/service/repository)
- Do NOT overload existing modules
- Create new module only if responsibility differs
- Group related functionality logically

---

## Refactoring Behavior

When modifying code:

- Prefer refactoring over rewriting
- Remove unused functions
- Replace duplicate logic with shared methods
- Maintain backward compatibility when possible

---

## Performance Awareness

Avoid:

- Unnecessary loops
- Repeated DB calls inside handlers
- Blocking operations in async handlers

Use async patterns properly when interacting with DB or IO.

---

Never generate redundant code.
Always prioritize reuse and maintainability.