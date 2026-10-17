#!/usr/bin/env node
'use strict';

const { parseArgs } = require('node:util');
const { installationRoot } = require('../../../../../core/cast/capabilities/tools/cast/lib/installation');
const media = require('./lib/media');

async function main() {
  const { values, positionals } = parseArgs({ allowPositionals: true, options: {
    help: { type: 'boolean', short: 'h' }, json: { type: 'boolean' }, model: { type: 'string' },
  } });
  if (values.help) {
    console.log(`onnx-asr — transcribe a local audio file without an external API\n\nUsage: onnx-asr transcribe FILE [--model ID] [--json]\n\n--model ID   onnx-asr model name (default: ${media.DEFAULT_MODEL})\n--json       print {text, model_id, source}; otherwise print the transcript\n-h, --help   show this help without loading a model\n\nSetup: .rbtv/config/onnx-asr/config.json in the installation holds model_path,\noptional python (executable) and threads (default 8). Paths are relative to the\ninstallation. Install weights and Python packages first; nothing is downloaded.\n\nExit: 0 success/help, 2 usage, 1 transcription or setup failure.`);
    return;
  }
  if (positionals.length !== 2 || positionals[0] !== 'transcribe') {
    console.error('onnx-asr: expected transcribe FILE; run onnx-asr -h');
    process.exitCode = 2;
    return;
  }
  const result = await media.operations['media.transcribe']({ file: positionals[1], model: values.model,
    workspace: installationRoot(process.cwd()) });
  console.log(values.json ? JSON.stringify(result) : result.text);
}

main().catch((error) => { console.error(`onnx-asr: ${error.message}`); process.exitCode = error.code?.startsWith('ERR_PARSE_ARGS') ? 2 : 1; }).finally(() => media.close());
