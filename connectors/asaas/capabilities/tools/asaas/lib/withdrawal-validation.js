'use strict';

// Asaas's half of Ignite's withdrawal validation. About 5 seconds after an outgoing operation, Asaas
// POSTs it to the account's validation URL and executes it only on APPROVED. Ignite's waking service
// loads this file by the connector name asaas (core/ignite/capabilities/tools/ignite/payment-webhook.js
// loadConnector) and answers from its payment gate; this file only says where Asaas calls, which header
// and variable hold the token, and how Asaas's body reads as an operation the gate can check.
//
// API
// path      '/asaas/withdrawal-validation'
// header    'asaas-access-token'
// tokenEnv  'ASAAS_WEBHOOK_TOKEN' (process environment, then the installation's .rbtv/config/env/.env)
// read(body) → { method, reference, operationId, amountCents, recipientKey } | { refuse: reason }
//   method is the asaas tool's own: TRANSFER is pix (the Pix key), BILL is bill (the digitable line), both
//   with the request id as externalReference. PIX_QR_CODE is qr and MOBILE_PHONE_RECHARGE is recharge: Asaas
//   takes no externalReference on those endpoints, so reference is null and the gate finds the request by
//   the operation id Ignite recorded when it paid. A top-up names its phone; a QR payment's body has no
//   payload, so recipientKey is null and the recorded id stands for it. Any other type is refused.
// Body shapes: https://docs.asaas.com/docs/mechanism-for-validating-withdrawals-via-webhooks.md

function cents(value) {
  return typeof value === 'number' && Number.isFinite(value) ? Math.round(value * 100) : null;
}

function idOf(value) {
  return value == null || value === '' ? null : String(value);
}

function read(body) {
  const type = body?.type;
  if (type === 'TRANSFER') {
    const op = body.transfer || {};
    return {
      method: 'pix', reference: op.externalReference || null, operationId: idOf(op.id),
      amountCents: cents(op.value), recipientKey: op.bankAccount?.pixAddressKey || null,
    };
  }
  if (type === 'BILL') {
    const op = body.bill || {};
    return {
      method: 'bill', reference: op.externalReference || null, operationId: idOf(op.id),
      amountCents: cents(op.value), recipientKey: op.identificationField || null,
    };
  }
  if (type === 'PIX_QR_CODE') {
    const op = body.pixQrCode || {};
    return { method: 'qr', reference: null, operationId: idOf(op.id), amountCents: cents(op.value), recipientKey: null };
  }
  if (type === 'MOBILE_PHONE_RECHARGE') {
    const op = body.mobilePhoneRecharge || {};
    return {
      method: 'recharge', reference: null, operationId: idOf(op.id),
      amountCents: cents(op.value), recipientKey: op.phoneNumber || null,
    };
  }
  return { refuse: `${type || 'an operation with no type'} is not paid through the payment gate` };
}

module.exports = {
  path: '/asaas/withdrawal-validation',
  header: 'asaas-access-token',
  tokenEnv: 'ASAAS_WEBHOOK_TOKEN',
  read,
};
