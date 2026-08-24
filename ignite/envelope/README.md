# ignite/envelope

Plan-time per-goal envelope compiler. See `component.md`.

```js
const { compile, compilePlanning } = require('./compiler');
const result = compile({
  workspaceRoot, goalId, rbtvRepo,
  namedRepos, projectFolder, credentialNames, extraPaths,
});
```
