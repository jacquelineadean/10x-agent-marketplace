#!/usr/bin/env bash
# Builds a small web app repo with a feature branch: a save button on the settings page.
set -eu
mkdir -p repo && cd repo
git init -q -b main
git config user.email dev@example.com && git config user.name "Dev"
mkdir -p src/pages tests
cat > package.json <<'J'
{ "name": "acme-web", "scripts": { "dev": "vite", "test": "vitest run" },
  "devDependencies": { "vite": "5.4.0", "vitest": "2.0.5", "@playwright/test": "1.47.0" } }
J
cat > src/pages/Settings.jsx <<'J'
export function Settings({ user, onChange }) {
  return (
    <main>
      <h1>Settings</h1>
      <label>Display name <input value={user.name} onChange={e => onChange({ ...user, name: e.target.value })} /></label>
    </main>
  );
}
J
echo "# acme-web" > README.md
git add -A && git commit -qm "chore: initial app"
git switch -qc feat/57-settings-save-button
cat > src/pages/Settings.jsx <<'J'
import { useState } from 'react';
import { saveProfile } from '../api/profile';

export function Settings({ user, onChange }) {
  const [status, setStatus] = useState('idle');
  async function save() {
    setStatus('saving');
    try { await saveProfile(user); setStatus('saved'); }
    catch { setStatus('error'); }
  }
  return (
    <main>
      <h1>Settings</h1>
      <label>Display name <input value={user.name} onChange={e => onChange({ ...user, name: e.target.value })} /></label>
      <button onClick={save} disabled={status === 'saving'}>Save</button>
      {status === 'saved' && <p role="status">Saved</p>}
      {status === 'error' && <p role="alert">Could not save. Try again.</p>}
    </main>
  );
}
J
mkdir -p src/api
cat > src/api/profile.js <<'J'
export async function saveProfile(user) {
  const res = await fetch('/api/profile', { method: 'PUT', body: JSON.stringify(user),
    headers: { 'Content-Type': 'application/json' } });
  if (!res.ok) throw new Error(`save failed: ${res.status}`);
}
J
git add -A && git commit -qm "feat(settings): add save button with saved and error states"
cat > tests/settings.test.jsx <<'J'
import { render, screen, fireEvent } from '@testing-library/react';
import { Settings } from '../src/pages/Settings';
test('shows Saved after a successful save', async () => { /* ... */ });
test('shows an error when the save fails', async () => { /* ... */ });
test('disables Save while saving', async () => { /* ... */ });
J
git add -A && git commit -qm "test(settings): cover saved, error and saving states"
