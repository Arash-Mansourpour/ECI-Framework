// eci-protocol0 — lightweight JS SDK (spec/policy/attest-client, no deps).
// Mirrors protocol0/spec.yaml thresholds so non-Python agents can comply.
'use strict';
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

const SPEC_PATH = path.join(__dirname, '..', '..', 'protocol0', 'spec.yaml');

function loadSpec() {
  // Minimal YAML subset parser: only the keys this SDK needs.
  const text = fs.readFileSync(SPEC_PATH, 'utf8');
  const actions = {};
  let current = null;
  for (const line of text.split('\n')) {
    const a = line.match(/^\s+-\s+name:\s+(\S+)/);
    if (a) { current = a[1]; actions[current] = { min_awareness: 0, min_obedience: 0, min_trust: 0, quorum: false }; continue; }
    if (!current) continue;
    const kv = line.match(/^\s+(min_awareness|min_obedience|min_trust|quorum):\s+(\S+)/);
    if (kv) {
      const [, k, v] = kv;
      actions[current][k] = (k === 'quorum') ? (v === 'true') : parseFloat(v);
    }
  }
  return { actions };
}

function check(spec, action, awareness, obedience, trust) {
  const rule = spec.actions[action];
  if (!rule) return { allow: false, reason: `unknown action ${action}` };
  for (const [k, v] of [['awareness', awareness], ['obedience', obedience], ['trust', trust]]) {
    if (v + 1e-9 < rule[`min_${k}`]) return { allow: false, reason: `${k} ${v} < ${rule[`min_${k}`]}` };
  }
  return { allow: true, reason: 'allow' };
}

function attestPayload(a) {
  return [a.agent_id, a.spec_version, a.awareness.toFixed(6), a.obedience.toFixed(6),
    a.trust.toFixed(6), a.timestamp.toFixed(3), a.nonce].join('|');
}

function issueAttestation(agentKeyHex, agentId, specVersion, awareness, obedience, trust) {
  const nonce = crypto.randomBytes(12).toString('hex');
  const a = { agent_id: agentId, spec_version: specVersion, awareness, obedience, trust, timestamp: Date.now() / 1000, nonce };
  const sig = crypto.createHmac('sha256', Buffer.from(agentKeyHex, 'hex')).update(attestPayload(a)).digest('hex');
  return { ...a, signature: sig };
}

function verifyAttestation(att, specVersion, agentKeyHex, maxAgeS = 300) {
  if (att.spec_version !== specVersion) return { ok: false, reason: 'spec pin mismatch' };
  if (Math.abs(Date.now() / 1000 - att.timestamp) > maxAgeS) return { ok: false, reason: 'stale' };
  const expect = crypto.createHmac('sha256', Buffer.from(agentKeyHex, 'hex')).update(attestPayload(att)).digest('hex');
  const ok = crypto.timingSafeEqual(Buffer.from(expect), Buffer.from(att.signature));
  return { ok, reason: ok ? '' : 'bad signature' };
}

module.exports = { loadSpec, check, issueAttestation, verifyAttestation };
