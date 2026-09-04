// node test.js — zero-dep self-test for the JS SDK.
const { loadSpec, check, issueAttestation, verifyAttestation } = require('./index');
const spec = loadSpec();
console.log('actions:', Object.keys(spec.actions).join(','));
console.log('vote gate (low awareness):', JSON.stringify(check(spec, 'vote', 0.0, 1, 1)));
console.log('vote gate (ok):', JSON.stringify(check(spec, 'vote', 0.9, 0.9, 0.9)));
const key = 'ab'.repeat(32);
const a = issueAttestation(key, 'alice', '0.1.0', 0.6, 0.8, 0.9);
console.log('attest verify:', JSON.stringify(verifyAttestation(a, '0.1.0', key)));
if (!verifyAttestation(a, '0.1.0', key).ok) { console.error('FAIL'); process.exit(1); }
if (check(spec, 'vote', 0.0, 1, 1).allow) { console.error('FAIL gate'); process.exit(1); }
console.log('JS SDK OK');
