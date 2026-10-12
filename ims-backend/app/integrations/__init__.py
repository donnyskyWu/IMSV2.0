# app/integrations - External system adapters (FW-H04)
"""
External system adapters.

Per FP-H04-01:
- Each external system has an interface + Real/Mock implementations
- Mode selected by integrations.<system>.mode config
- Unified timeout, retry, circuit breaker
- Error codes mapped per system

Systems:
- dingtalk: DingTalk IMS app (5003 on timeout)
- dingtalk_attendance: DingTalk attendance app (FW-H07)
- football_live: Football live room read-only (1271-1273)
- train_ai: Training AI (1106-1109)
"""
