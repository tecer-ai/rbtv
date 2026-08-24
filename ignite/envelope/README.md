# ignite/envelope

Plan-time per-goal envelope compiler and launch consumer. See `component.md`.

```js
const { compile, compilePlanning } = require('./compiler');
const { admitLaunch } = require('./launch');
const { resolveCredentials, injectDeclaredEnv } = require('./credentials');
const { writeConfigShims } = require('./shims');
const { writeWallReport } = require('./wall-report');
```
