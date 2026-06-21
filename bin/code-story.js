#!/usr/bin/env node
/*
 * code-story CLI (npm entry point).
 * Thin wrapper over install.sh, which lives next to the engine in this package.
 * Usage:
 *   code-story enable [repo]   enable code-story in a repo (default: current repo)
 *   code-story global          run the hook for all your repos (global core.hooksPath)
 *   code-story help
 */
"use strict";
const { spawnSync } = require("child_process");
const path = require("path");

const pkgRoot = path.resolve(__dirname, "..");
const installer = path.join(pkgRoot, "install.sh");

const verbToFlag = { enable: "--enable", global: "--global", help: "--help" };
const argv = process.argv.slice(2);
if (argv.length && verbToFlag[argv[0]]) {
  argv[0] = verbToFlag[argv[0]];
} else if (argv.length === 0) {
  argv.push("--help");
}

const res = spawnSync("sh", [installer, ...argv], { stdio: "inherit" });
process.exit(res.status === null ? 1 : res.status);
