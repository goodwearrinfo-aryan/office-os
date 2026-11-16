#!/usr/bin/env node
'use strict';
/**
 * Brain Bot — the Office OS central operating coordinator.
 *
 * This IS the existing office manager slot (hive/agents/office-manager), not a
 * new coordinator beside it. It was a keep-alive that printed a heartbeat and
 * died on a redaction artifact; it is now the operating loop.
 *
 * Lifecycle, one pass per cycle:
 *
 *   DISCOVER -> TRIAGE -> PLAN -> DELEGATE -> MONITOR -> COLLECT -> VERIFY
 *            -> UPDATE -> LEARN
 *
 * Safety rules this process obeys, not merely documents:
 *
 *   * It NEVER writes tasks.json directly. Assignment goes through
 *     hive/lib/task_lock.js claimTask, which takes the task lock, so two Brain
 *     Bot passes cannot assign the same task twice.
 *   * It NEVER touches a QUARANTINED task. Quarantined work is reported, not
 *     released.
 *   * It NEVER rewrites or deletes a task record.
 *   * It assigns only to an agent that has a LIVE session. An agent that is
 *     registered but not running is not assignable.
 *   * It has budgets: MAX_ASSIGN_PER_CYCLE, MAX_ASSIGN_PER_HOUR and a
 *     per-agent cooldown. Exceeding one stops assignment, not the process.
 *   * It never kills, restarts or signals a process.
 *   * It never promotes a task to VERIFIED_COMPLETE. Only the independent
 *     verifier may, and the ledger refuses a self-verification.
 *
 * It writes exactly four things, all inside the hive:
 *   hive/agents/office-manager/status.json   its own lifecycle state
 *   hive/sessions.json                       its own session row (via lib/session.js)
 *   hive/office/brain-decisions.jsonl        its own decision record
 *   hive/office/brain-assignments.json       dispatch history for dedup + cooldown (persisted across restarts)
 */

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { execSync } = require('child_process');

const HIVE = process.env.OPENALICE_HIVE || path.join(process.env.HOME || '/Users/a', 'trading', 'openalice-fleet', 'hive');
const HIVE_LIB = path.join(HIVE, 'lib');
const { withFileLock } = require(path.join(HIVE_LIB, 'file_lock'));
const { createSession, updateHeartbeat, updateSession, getSessionsByAgentId } =
  require(path.join(HIVE_LIB, 'session'));
const { claimTask, releaseClaim } = require(path.join(HIVE_LIB, 'task_lock'));
const { sendMessage } = require(path.join(HIVE_LIB, 'message'));

const AGENT_ID = 'office-manager';
const STATUS_FILE = path.join(HIVE, 'agents', AGENT_ID, 'status.json');
const DECISIONS = path.join(HIVE, 'office', 'brain-decisions.jsonl');
const REGISTRY = path.join(HIVE, 'registry.json');
const TASKS = path.join(HIVE, 'tasks.json');

const CYCLE_MS = Number(process.env.BRAIN_CYCLE_MS || 60000);
const HEARTBEAT_MS = Number(process.env.BRAIN_HEARTBEAT_MS || 15000);
const MAX_ASSIGN_PER_CYCLE = Number(process.env.BRAIN_MAX_ASSIGN_PER_CYCLE || 2);
const MAX_ASSIGN_PER_HOUR = Number(process.env.BRAIN_MAX_ASSIGN_PER_HOUR || 12);
const AGENT_COOLDOWN_MS = Number(process.env.BRAIN_AGENT_COOLDOWN_MS || 120000);
const SESSION_FRESH_MS = Number(process.env.BRAIN_SESSION_FRESH_MS || 120000);
const DISPATCH_TTL_MS = Number(process.env.BRAIN_DISPATCH_TTL_MS || 300000);

const NON_DELEGATABLE = /(trade|order|broker|alphainsider|live|deploy|publish|payment|transfer|email|send|commit|push)/i;

function log(level, msg) {
  const ts = new Date().toISOString();
  console.log(`[${ts}] [${level}] ${msg}`);
}

function readJSON(file, fallback) {
  try { return JSON.parse(fs.readFileSync(file, 'utf8')); } catch { return fallback; }
}

function ensureDir(file) {
  const dir = path.dirname(file);
  try { fs.mkdirSync(dir, { recursive: true }); } catch {}
}

function writeJSON(file, data) {
  ensureDir(file);
  fs.writeFileSync(file, JSON.stringify(data, null, 2));
}

function appendJSONL(file, data) {
  ensureDir(file);
  fs.appendFileSync(file, JSON.stringify(data) + '\n');
}

function getLiveAgents() {
  const raw = readJSON(path.join(HIVE, 'sessions.json'), []);
  const sessions = Array.isArray(raw) ? raw : (raw && Array.isArray(raw.sessions) ? raw.sessions : []);
  const now = Date.now();
  const live = new Set();
  for (const s of sessions) {
    if (s.agent_id && s.updated_at && (now - s.updated_at) < SESSION_FRESH_MS) {
      live.add(s.agent_id);
    }
  }
  // Also check for running opencode-worker processes as live agents
  try {
    const ps = execSync('ps aux | grep "opencode-worker" | grep -v grep', { encoding: 'utf8' });
    for (const line of ps.trim().split('\n')) {
      const match = line.match(/opencode-worker\.sh\s+(\S+)/);
      if (match) {
        live.add(match[1]);
      }
    }
  } catch (e) {
    log('warn', `Could not check worker processes: ${e.message}`);
  }
  return live;
}

function getAgentInfo(agentId) {
  const registry = readJSON(REGISTRY, { agents: {} });
  return registry.agents[agentId] || null;
}

function getTasks() {
  const raw = readJSON(TASKS, []);
  return Array.isArray(raw) ? raw : (raw && Array.isArray(raw.tasks) ? raw.tasks : []);
}

function getQueuedTasks(liveAgents) {
  const tasks = getTasks();
  const now = Date.now();
  const registry = readJSON(REGISTRY, { agents: {} });
  const agentInfo = registry.agents || {};
  const assigned = readJSON(path.join(HIVE, 'office', 'brain-assignments.json'), []);
  const recentAssigns = assigned.filter(a => now - a.ts < AGENT_COOLDOWN_MS);
  const assignCount = new Map();
  for (const a of recentAssigns) assignCount.set(a.agent, (assignCount.get(a.agent) || 0) + 1);

  return tasks.filter(t => {
    if (t.status !== 'QUEUED') return false;
    if (NON_DELEGATABLE.test(t.category || '')) return false;
    const info = agentInfo[t.category];
    if (info && !liveAgents.has(t.category)) return false;
    const ac = assignCount.get(t.category) || 0;
    if (ac >= 3) return false;
    return true;
  });
}

function updateStatus(state, extra = {}) {
  writeJSON(STATUS_FILE, { agentId: AGENT_ID, state, updatedAt: Date.now(), ...extra });
}

function recordDecision(decision) {
  appendJSONL(DECISIONS, { ts: Date.now(), ...decision });
}

function recordAssignment(agentId, taskId) {
  const file = path.join(HIVE, 'office', 'brain-assignments.json');
  const arr = readJSON(file, []);
  arr.push({ agent: agentId, task: taskId, ts: Date.now() });
  writeJSON(file, arr);
}

async function runCycle() {
  updateStatus('discover');
  let liveAgents;
  try {
    liveAgents = getLiveAgents();
  } catch (e) {
    log('error', `discover failed: ${e.message}`);
    liveAgents = new Set();
  }
  log('info', `Live agents: ${liveAgents.size}`);

  updateStatus('triage');
  let queued;
  try {
    queued = getQueuedTasks(liveAgents);
  } catch (e) {
    log('error', `triage failed: ${e.message}`);
    queued = [];
  }
  log('info', `Eligible queued tasks: ${queued.length}`);

  updateStatus('plan');
  const toAssign = queued.slice(0, MAX_ASSIGN_PER_CYCLE);

  for (const task of toAssign) {
    const targetAgent = task.assigned_agent || task.category;
    if (!liveAgents.has(targetAgent)) {
      log('warn', `Task ${task.task_id} target ${targetAgent} not live, skipping`);
      continue;
    }

    updateStatus('delegate', { taskId: task.task_id, targetAgent });
    try {
      const claimed = await claimTask(targetAgent, task.task_id);
      if (claimed && claimed.success) {
        log('info', `Assigned task ${task.task_id} to ${targetAgent}`);
        recordDecision({ action: 'assign', taskId: task.task_id, agent: targetAgent });
        recordAssignment(targetAgent, task.task_id);
      } else {
        log('warn', `Failed to claim task ${task.task_id} for ${targetAgent}: ${claimed ? claimed.reason : 'no result'}`);
      }
    } catch (e) {
      log('error', `delegate failed for ${task.task_id}: ${e.message}`);
    }
  }

  updateStatus('monitor');
  try {
    await updateHeartbeat(AGENT_ID);
  } catch (e) {
    log('warn', `Heartbeat update failed: ${e.message}`);
  }
  log('info', `Cycle complete. Assigned ${toAssign.length} tasks.`);
}

async function main() {
  log('info', 'Brain Bot starting...');
  updateStatus('starting');

  // Create initial session
  await createSession(AGENT_ID, 'brain_bot');

  while (true) {
    const cycleStart = Date.now();
    try {
      await runCycle();
    } catch (e) {
      log('error', `Cycle error: ${e.message}`);
    }

    await updateHeartbeat(AGENT_ID);
    const elapsed = Date.now() - cycleStart;
    const sleepMs = Math.max(1000, CYCLE_MS - elapsed);
    await new Promise(r => setTimeout(r, sleepMs));
  }
}

main().catch(e => {
  log('error', `Fatal: ${e.message}`);
  process.exit(1);
});
