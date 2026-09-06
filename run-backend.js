const { spawn, execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const rootDir = path.resolve(__dirname);

function getPython() {
  const venvWin = path.join(rootDir, '.venv', 'Scripts', 'python.exe');
  const venvPosix = path.join(rootDir, '.venv', 'bin', 'python');

  if (fs.existsSync(venvWin)) return venvWin;
  if (fs.existsSync(venvPosix)) return venvPosix;

  if (process.platform === 'win32') {
    try {
      execSync('py -0', { stdio: 'ignore' });
      return 'py';
    } catch {
      return 'python';
    }
  }

  return 'python3';
}

const pyBin = getPython();
const runBackendPy = path.join(rootDir, 'run_backend.py');

const child = spawn(pyBin, [runBackendPy], {
  cwd: rootDir,
  stdio: 'inherit',
  shell: true,
});

child.on('exit', (code) => {
  process.exit(code || 0);
});

child.on('error', (err) => {
  console.error('Failed to start backend server:', err);
  process.exit(1);
});
