// Bootstrap runs inside Central, using its official account tasks and HTTP API.
// Mandi never needs Central's database credentials or the Docker socket.
import { execFileSync } from 'node:child_process';
import { writeFileSync } from 'node:fs';

const env = process.env;
const base = env.CENTRAL_BOOTSTRAP_URL || 'http://localhost:8383/v1';
const admin = [env.ODK_ADMIN_EMAIL, env.ODK_ADMIN_PASSWORD];
const integration = [env.ODK_EMAIL, env.ODK_PASSWORD];
const authorization = pair => `Basic ${Buffer.from(pair.join(':')).toString('base64')}`;
async function response(method, path, body, credentials = admin) {
  return fetch(base + path, {
    method,
    // Central only allows Basic auth when the request looks like HTTPS. This
    // request stays inside the private Docker network.
    headers: { Authorization: authorization(credentials), 'Content-Type': 'application/json', 'X-Forwarded-Proto': 'https' },
    body: body === undefined ? undefined : JSON.stringify(body), redirect: 'error',
    signal: AbortSignal.timeout(15000),
  });
}
async function api(method, path, body, credentials) {
  const result = await response(method, path, body, credentials);
  if (!result.ok) throw new Error(`Central bootstrap ${method} ${path} failed (${result.status}). Check configured accounts and project ID.`);
  return result.json();
}
function accountTask(task) {
  // Passwords are inherited through the environment, never command-line arguments.
  // Central's task runner requires a real script path; `node -e` has none.
  try { execFileSync('node', ['/opt/mandi/account-task.cjs', task], { cwd: '/usr/odk', env, stdio: ['ignore', 'pipe', 'pipe'] }); }
  catch (error) {
    const details = error.stderr?.toString().trim();
    throw new Error(`Central ${task} failed. An existing administrator may use a different password; existing passwords are never reset automatically.${details ? `\n${details}` : ''}`);
  }
}

let current;
for (let attempt = 0; attempt < 180; attempt++) {
  try {
    current = await response('GET', '/users/current');
    if (current.status === 200 || current.status === 401) break;
  } catch { /* Wait for Central's migrations and HTTP listener. */ }
  await new Promise(resolve => setTimeout(resolve, 2000));
}
if (!current || ![200, 401].includes(current.status)) throw new Error('Central did not become ready for bootstrap.');
if (current.status === 401) {
  // Recover an interrupted first setup: the account may already exist.
  try { accountTask('createUser'); } catch { /* Existing account; never reset its password. */ }
  try { accountTask('promoteUser'); } catch { /* Already promoted on an earlier run. */ }
  const verified = await response('GET', '/users/current');
  if (verified.status !== 200) {
    throw new Error('Central has an administrator account, but ODK_ADMIN_PASSWORD does not match it. Set the existing password in .env or move the Central database volume aside.');
  }
} else {
  const users = await response('GET', '/users');
  if (users.status === 403) {
    try { accountTask('promoteUser'); } catch { /* Reported by the check below. */ }
    const verified = await response('GET', '/users');
    if (!verified.ok) throw new Error(`Central administrator promotion check failed (${verified.status}).`);
  } else if (!users.ok) throw new Error(`Central account check failed (${users.status}).`);
}
const projectId = Number(env.ODK_PROJECT_ID || 1);
if (!Number.isSafeInteger(projectId) || projectId < 1) throw new Error('ODK_PROJECT_ID must be a positive integer.');
const projects = await api('GET', '/projects');
if (!projects.some(project => project.id === projectId)) {
  const project = await api('POST', '/projects', { name: 'Mandi inspections' });
  if (project.id !== projectId) throw new Error(`Central allocated project ${project.id}. Set ODK_PROJECT_ID accordingly and restart Central.`);
}
const users = await api('GET', '/users');
let user = users.find(item => item.email === env.ODK_EMAIL);
if (!user) user = await api('POST', '/users', { email: env.ODK_EMAIL, password: env.ODK_PASSWORD, displayName: 'Mandi integration' });
const assignments = await api('GET', `/projects/${projectId}/assignments`);
if (!assignments.some(item => item.actorId === user.id)) {
  // A concurrent/repeated run may still race here; 409 is not a failure.
  const assigned = await response('POST', `/projects/${projectId}/assignments/manager/${user.id}`);
  if (!assigned.ok && assigned.status !== 409) {
    throw new Error(`Central bootstrap POST /projects/${projectId}/assignments/manager/${user.id} failed (${assigned.status}). Check configured accounts and project ID.`);
  }
}
await api('GET', '/users/current', undefined, integration);
await api('GET', `/projects/${projectId}`, undefined, integration);
writeFileSync('/tmp/mandi-central-ready', 'ready\n');
console.log('Central is ready: administrator, integration account, and inspection project configured.');
