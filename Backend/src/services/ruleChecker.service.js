const { spawn } = require('child_process');
const path = require('path');

const SCRIPT = path.join(__dirname, '..', '..', 'rule_checker.py');

function runRuleChecker(cliInputs) {
    return new Promise((resolve, reject) => {
        const py = spawn('python', [SCRIPT]);
        let stdout = '';
        let stderr = '';

        py.stdout.on('data', (d) => (stdout += d));
        py.stderr.on('data', (d) => (stderr += d));

        py.on('close', (code) => {
            if (code !== 0) return reject(new Error(stderr || `rule_checker exited with code ${code}`));
            try {
                resolve(JSON.parse(stdout));
            } catch {
                reject(new Error('Failed to parse rule_checker output'));
            }
        });

        py.stdin.write(JSON.stringify(cliInputs));
        py.stdin.end();
    });
}

module.exports = runRuleChecker;
