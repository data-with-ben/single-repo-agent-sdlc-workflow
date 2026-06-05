/**
 * Playwright browser installer with corporate certificate support.
 *
 * Use this when `npx playwright install` fails with TLS/certificate errors
 * (common on machines behind a corporate proxy that rewrites TLS).
 *
 * Configuration via environment variables:
 *   NODE_EXTRA_CA_CERTS         Path to a CA bundle (e.g. C:\Certs\cacert.pem).
 *                               If unset, the script runs without injecting one.
 *   PLAYWRIGHT_INSECURE_TLS     Set to "1" to disable TLS verification entirely
 *                               (last-resort; prefer NODE_EXTRA_CA_CERTS).
 *   PLAYWRIGHT_BROWSER          Browser to install (default: chromium).
 *
 * Usage:
 *   cd <e2e-project-path>
 *   NODE_EXTRA_CA_CERTS=/path/to/cacert.pem node <repo-root>/.claude/skills/e2e-tests/scripts/install-browsers.js
 */

const { execSync } = require('child_process');

const browser = process.env.PLAYWRIGHT_BROWSER || 'chromium';
const caCerts = process.env.NODE_EXTRA_CA_CERTS;
const insecure = process.env.PLAYWRIGHT_INSECURE_TLS === '1';

if (!caCerts && !insecure) {
  console.warn(
    'Warning: NODE_EXTRA_CA_CERTS is not set. If installation fails with a TLS error,\n' +
      '  set NODE_EXTRA_CA_CERTS to your corporate CA bundle and re-run, e.g.:\n' +
      '  NODE_EXTRA_CA_CERTS=C:\\\\Certs\\\\cacert.pem node install-browsers.js'
  );
}

if (insecure) {
  process.env.NODE_TLS_REJECT_UNAUTHORIZED = '0';
  console.warn('Warning: PLAYWRIGHT_INSECURE_TLS=1 — TLS verification disabled.');
}

if (caCerts) {
  console.log(`Using CA bundle: ${caCerts}`);
}

try {
  console.log(`Installing Playwright browser: ${browser}...`);
  execSync(`npx playwright install ${browser}`, {
    stdio: 'inherit',
    env: process.env,
  });
  console.log(`Browser '${browser}' installed successfully.`);
} catch (error) {
  console.error('Installation failed:', error.message);
  process.exit(1);
}
