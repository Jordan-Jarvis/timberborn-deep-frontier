// This machine's Timberborn and tool paths, written by tools/setup_dev.py
// (tools/dev-environment.json, not tracked). A missing file or entry is an
// error that says to run setup; nothing here guesses a path.
//   const dev = await devEnvironment(root, ['workshopContent']);
import {readFile} from 'node:fs/promises';
import {resolve} from 'node:path';

export async function devEnvironment(root, required = []) {
  const path = resolve(root, 'tools', 'dev-environment.json');
  const text = await readFile(path, 'utf8').catch(() => {
    throw new Error(`${path} is missing: run "python tools/setup_dev.py" first.`);
  });
  const dev = JSON.parse(text);
  for (const key of required)
    if (!dev[key]) throw new Error(`"${key}" is not set in ${path}: re-run "python tools/setup_dev.py".`);
  return dev;
}
