# STANDUP
**Date:** Friday, November 13th, 2026
**Time:** 12:50 AM IST (2026-11-13 04:50 UTC)

## Top 3 Outcomes
1. All 5 workers have standing duty tasks (`- [ ]`) assigned and ready for this run
2. No policy breaks detected: trader confirmed live_orders_allowed=false (paper trading only), codex reported only observations (no git push, no deletes, no secrets)
3. Harness model health checked: 429 rate limits observed, recommendations documented for throttle/backup auth; autonomy evidence_ledger.py restored from backup

## Blockers
- 7 com.aryan launch agents not running: openalice-holdout-backup, opencode-db-compact, office-hud-deployed-check, monte-carlo-validation, openalice-ts-momentum-holdout, git-autopush, openalice-pipeline
- Gateway rate limiting: 429 errors in ~/Library/Logs/openclaw/gateway.log affecting harness model health checks
- qoder-office and office-* directories do not exist on the mini

## Needs-Human Items
- Gateway API quota/key management may require human attention to resolve 429 rate limiting
- Launch agent restarts may require human intervention to reschedule com.aryan jobs

## Tasks Assigned This Run
- **trader:** `- [ ] Check paper books: Polymarket paper bot, OpenAlice paper trader, scalp lab. Report open positions, feed freshness, P&L, confirm live_orders_allowed=false.`
- **watchdog:** `- [ ] Check mini: failing com.aryan.* launchd jobs, stale outputs, disk/memory/swap, backup status. Give exact fix commands; do not run destructive fixes.`
- **autonomy:** `- [ ] Check other offices and fleets: OpenAlice fleet, nvidia-office, qoder-office, office-*. Report running/stuck status and overlaps/conflicts.`
- **harness:** `- [ ] Check NVIDIA model health: 429 vs 200 in gateway.log, auth profile cooldowns (status only), token use by nvidia-office. Recommend load changes.`
- **codex:** `- [ ] Check repos under ~/office: dirty trees, unpushed commits, failing tests or CI notes. Report only; never commit, push, reset or delete.`

**Open tasks per worker:** 1 each (standing duty). No worker has more than 2 open `- [ ]` tasks.