// Every name the web client reads is defined somewhere (nexel-worlds#174): ESLint's no-undef, over the page's
// scripts as the page loads them (web/scripts.txt's list, in its order). The classic scripts of web/index.html share one global scope, so a name one of
// them declares at its top is a global for all; each file's top-level names are found by ESLint's own scope analysis
// (not a regex), then every file is linted with them and the browser's globals. A name a split leaves behind
// (hd_stands.js used winMap, which it was not given: #158) fails here, in the lint job, not in the browser run.
//
//   npm install --no-save --no-package-lock eslint@9.39.5 globals@16.5.0 && node tools/undef_check.mjs   (CI: the web lint job)
//
// Exit 1 with each undefined name and where it is read.

import {readFileSync} from "node:fs";
import {Linter} from "eslint";
import globals from "globals";

const WEB = new URL("../src/nexel_worlds/web/", import.meta.url);
const page = readFileSync(new URL("index.html", WEB), "utf8");
const inline = Object.fromEntries([...page.matchAll(/<script>\n([\s\S]*?)<\/script>/g)].map((m, i) => [`index.html#${i + 1}`, m[1]]));   // (the page's own scripts: bookPx, TITLE_DY...)
const listed = readFileSync(new URL("scripts.txt", WEB), "utf8").split("\n").map((l) => l.trim()).filter((l) => l && !l.startsWith("#"));   // (the page's scripts, in their order: web/scripts.txt, as web_bundle.py scripts reads it)
const classic = [...Object.keys(inline), ...listed];
classic.push("local.js");                // (the published page's: tools/build_pages.py puts it in, the server in the tab: LocalSocket)
const modules = ["local_worker.js"];     // (a module worker: its own scope, imports)
const read = (name) => inline[name] ?? readFileSync(new URL("js/" + name, WEB), "utf8");
const linter = new Linter({configType: "flat"});
const lang = (sourceType) => ({ecmaVersion: "latest", sourceType});

// the names each classic script declares at its top (const, let, var, function, class): the page's shared globals
const shared = {};
for (const name of classic) {
  const messages = linter.verify(read(name), {languageOptions: lang("script"), rules: {}}, name + ".js");
  const bad = messages.find((m) => m.fatal);
  if (bad) { console.error(`${name}:${bad.line}: ${bad.message}`); process.exit(1); }
  for (const v of linter.getSourceCode().scopeManager.globalScope.variables) if (v.defs.length) shared[v.name] = "writable";
}

const browser = {...globals.browser, ...globals.es2024, module: "readonly"};   // (module: a file also read by node, behind typeof: wayout.js)
let found = 0;
for (const [name, sourceType] of [...classic.map((n) => [n, "script"]), ...modules.map((n) => [n, "module"])]) {
  const g = sourceType === "script" ? {...browser, ...shared} : {...globals.worker, ...globals.es2024};
  const messages = linter.verify(read(name), {languageOptions: {...lang(sourceType), globals: g}, rules: {"no-undef": "error"}}, name + ".js");
  for (const m of messages) { found++; console.log(`src/nexel_worlds/web/${name.startsWith("index.html") ? "" : "js/"}${name}:${m.line}:${m.column}: ${m.message}`); }
}
console.log(found ? `${found} undefined name(s)` : `no undefined names in ${classic.length + modules.length} files`);
process.exit(found ? 1 : 0);
