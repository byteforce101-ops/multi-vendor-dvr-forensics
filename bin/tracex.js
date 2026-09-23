#!/usr/bin/env node

const { spawnSync, spawn } = require('child_process');
const { existsSync } = require('fs');
const path = require('path');

const repoUrl = 'git+https://github.com/byteforce101-ops/multi-vendor-dvr-forensics.git';

function findWorkingPython(rootDir) {
  const venvPyWin = path.join(rootDir, '.venv', 'Scripts', 'python.exe');
  const venvPyNix = path.join(rootDir, '.venv', 'bin', 'python');

  if (existsSync(venvPyWin)) return venvPyWin;
  if (existsSync(venvPyNix)) return venvPyNix;

  const candidates = process.platform === 'win32'
    ? ['py', 'python', 'python3']
    : ['python3', 'python'];

  for (const cmd of candidates) {
    try {
      const res = spawnSync(cmd, ['-c', 'import sys; sys.exit(0)'], { shell: true, stdio: 'ignore' });
      if (res.status === 0) return cmd;
    } catch (e) {}
  }
  return process.platform === 'win32' ? 'py' : 'python3';
}

const args = process.argv.slice(2);
const rootDir = path.resolve(__dirname, '..');
const localMain = path.join(rootDir, 'main.py');
const pythonCmd = findWorkingPython(rootDir);

if (existsSync(localMain)) {
  const pyEnv = { ...process.env, PYTHONPATH: rootDir };
  const child = spawn(pythonCmd, ['-m', 'backend.cli.main', ...args], {
    stdio: 'inherit',
    env: pyEnv,
    shell: true
  });
  child.on('exit', (code) => process.exit(code || 0));
} else {
  console.log('\x1b[36m%s\x1b[0m', '=== TraceX DVR Forensics Platform ===');
  console.log(`[+] Using Python executable: ${pythonCmd}`);

  const checkProcess = spawnSync(pythonCmd, ['-c', 'import backend.cli.main'], {
    shell: true,
    stdio: 'ignore'
  });

  if (checkProcess.status === 0) {
    const runProcess = spawn(pythonCmd, ['-m', 'backend.cli.main', ...args], {
      stdio: 'inherit',
      shell: true
    });
    runProcess.on('exit', (exitCode) => process.exit(exitCode || 0));
  } else {
    console.log('[+] Installing TraceX CLI engine package...');
    const installProcess = spawnSync(pythonCmd, ['-m', 'pip', 'install', '--quiet', repoUrl], {
      stdio: 'inherit',
      shell: true
    });

    if (installProcess.status === 0) {
      const runProcess = spawn(pythonCmd, ['-m', 'backend.cli.main', ...args], {
        stdio: 'inherit',
        shell: true
      });
      runProcess.on('exit', (exitCode) => process.exit(exitCode || 0));
    } else {
      console.error('[!] Installation failed. Ensure Python 3.11+ and Git are installed.');
      process.exit(1);
    }
  }
}
