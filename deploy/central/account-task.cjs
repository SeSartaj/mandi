// Run one upstream Central account task without exposing passwords in argv.
// Central's task runner needs a real script path (it calls Path.parse on
// process.argv[1]), so `node -e` cannot be used.
const { run } = require('/usr/odk/lib/task/task');
const tasks = require('/usr/odk/lib/task/account');

const task = process.argv[2];
if (!['createUser', 'promoteUser'].includes(task)) {
  console.error(`Unsupported account task: ${task}`);
  process.exit(2);
}
run(tasks[task](
  process.env.ODK_ADMIN_EMAIL,
  task === 'createUser' ? process.env.ODK_ADMIN_PASSWORD : undefined,
));
