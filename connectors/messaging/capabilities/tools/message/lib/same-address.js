'use strict';

// Whether two service addresses name the same account or person, compared in the service's own form:
// a mail address only whole (case-insensitive), a phone identifier (a number or a WhatsApp jid) by its
// digits. Digit stripping never compares mail addresses: a1@x.com and b1@y.com are two addresses.
// Used by the message port's owner check and by Ignite's outbox account binding.
function sameAddress(value, wanted) {
  const text = String(value ?? '').trim();
  const want = String(wanted ?? '').trim();
  if (!text || !want) return false;
  if (want.includes('@') && !isPhoneJid(want)) return !isPhoneJid(text) && text.toLowerCase() === want.toLowerCase();
  if (text.includes('@') && !isPhoneJid(text)) return false;
  const digits = text.replace(/\D/g, '');
  return digits !== '' && digits === want.replace(/\D/g, '');
}

function isPhoneJid(text) {
  return /(@|\.)s\.whatsapp\.net$/i.test(text) || /@g\.us$/i.test(text);
}

module.exports = { sameAddress };

if (require.main === module) {
  const assert = require('node:assert/strict');
  assert.equal(sameAddress('A1@X.com', 'a1@x.com'), true);
  assert.equal(sameAddress('a1@x.com', 'b1@y.com'), false);
  assert.equal(sameAddress('5511999990000@s.whatsapp.net', '+55 11 99999-0000'), true);
  assert.equal(sameAddress('5511999990000@s.whatsapp.net', '5511999990000'), true);
  assert.equal(sameAddress('15550000001', '15550000009'), false);
  assert.equal(sameAddress('owner1@x.com', '1'), false);
  console.log('PASS same-address');
}
