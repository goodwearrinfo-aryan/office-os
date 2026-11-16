# OFFICE BOARD

Hosted on the Mac mini. Manager: **main** (every 2h, writes STANDUP.md). Workers run only when their inbox has a `- [ ]` task.

| Agent | Area | Standing duty |
|---|---|---|
| trader | Trading (paper) | Check the paper books: Polymarket paper bot (~/office/polymarket), OpenAlice paper trader, scalp lab. Report open paper positions, feed freshness, paper P&L, and confirm live_orders_allowed=false. |
| watchdog | Ops | Check the mini: failing com.aryan.* launchd jobs (exit != 0), stale outputs, disk, memory and swap, last backup status. Give the exact fix command for each problem; do not run destructive fixes. |
| autonomy | Fleet | Check the other offices and fleets: OpenAlice fleet, nvidia-office, qoder-office, office-* jobs. Report what is running, what is stuck, and any overlap or conflict between them. |
| harness | LLM | Check NVIDIA model health: 429 vs 200 in ~/Library/Logs/openclaw/gateway.log, auth profile cooldowns (status only, never print key values), and token use by nvidia-office. Recommend load changes. |
| codex | Eng | Check repos under ~/office: dirty trees, unpushed commits, failing tests or CI notes. Report only; never commit, push, reset or delete. |
