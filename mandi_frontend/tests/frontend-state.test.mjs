import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import ts from 'typescript';
import axios from 'axios';
import i18next from 'i18next';

const root = path.resolve(import.meta.dirname, '..');
const out = path.join(root, 'node_modules/.cache/mandi-state-tests');
await fs.mkdir(out, {recursive:true});
async function compile(source, name, replacements={}) {
  let content = await fs.readFile(path.join(root, 'src', source), 'utf8');
  for (const [from, to] of Object.entries(replacements)) content = content.replaceAll(from, to);
  const result = ts.transpileModule(content, {compilerOptions:{module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2023}});
  const file = path.join(out, `${name}.mjs`);
  await fs.writeFile(file, result.outputText);
  return import(file);
}
const {readInspectionFilters,writeInspectionFilters,validDateRange} = await compile('features/inspections/filter-state.ts','filters');
const {paginationState} = await compile('components/public/pagination-state.ts','pagination');
await i18next.init({lng:'en',resources:{en:{translation:{}}}});
const {api,errorMessage} = await compile('lib/api.ts','api',{'import.meta.env.VITE_API_URL':'""'});

test('inspection filter links round-trip all supported filters and preserve unrelated URL state', () => {
  const values = {date_from:'2026-01-01',date_to:'2026-11-15',kind:'brief',approved:'false',establishment_kind:'pharmacy',province:'Kabul',inspector_id:'7',checklist_id:'3'};
  const next = writeInspectionFilters(new URLSearchParams('page=5&ordering=-date&unknown=x'),values);
  assert.deepEqual(readInspectionFilters(next),values);
  assert.equal(next.get('page'),'1');
  assert.equal(next.get('ordering'),'-date');
  assert.equal(next.get('unknown'),'x');
  const cleared = writeInspectionFilters(next,{});
  assert.deepEqual(readInspectionFilters(cleared),{});
  assert.deepEqual(readInspectionFilters(new URLSearchParams('approved=__all__&province=&unknown=x')),{});
});

test('date filters allow open bounds and equal dates, and reject reversed bounds', () => {
  assert.equal(validDateRange('2026-11-15','2026-11-15'),true);
  assert.equal(validDateRange('2026-11-15','2026-11-14'),false);
  assert.equal(validDateRange('','2026-11-14'),true);
  assert.equal(validDateRange('2026-11-15',''),true);
});

test('pagination handles invalid inputs, empty data and out-of-range pages', () => {
  assert.deepEqual(paginationState('-1','bad',0,[10,20]),{page:1,pageSize:10,totalPages:1,options:[10,20],pages:[1]});
  assert.equal(paginationState('999','20',45,[10,20]).page,3);
  assert.equal(paginationState('1.5','10000',45,[10,20]).pageSize,10);
  assert.deepEqual(paginationState('1','10',0,[-1,0,NaN]).options,[10]);
});

test('errors give actionable fallback text without exposing server HTML or nested internal objects', () => {
  const error = (status,data) => new axios.AxiosError('failure',undefined,{},undefined,{status,data});
  assert.match(errorMessage(error(500,'<html>private traceback</html>')),/temporarily unavailable/);
  assert.match(errorMessage(error(404,{})),/could not be found/);
  assert.equal(errorMessage(error(400,{non_field_errors:['Invalid combination.']})),'Invalid combination.');
  assert.equal(errorMessage(error(400,{name:['Required.']})),'name: Required.');
  assert.doesNotMatch(errorMessage(error(400,{internal:{secret:'hidden'}})),/secret|hidden|object Object/);
  assert.match(errorMessage(new axios.AxiosError('network')),/Check your connection/);
});

test('only a 401 for the current authenticated session expires it; 403 and stale sessions do not', async () => {
  const storage = new Map();
  globalThis.sessionStorage = {getItem:key=>storage.get(key)??null,removeItem:key=>storage.delete(key)};
  const events = [];
  globalThis.window = {dispatchEvent:event=>events.push(event.type)};
  const reject = (status, callback) => async config => {
    callback?.();
    throw new axios.AxiosError('failure',undefined,config,undefined,{status,data:{detail:'Denied'}});
  };
  await assert.rejects(api.get('/test',{adapter:reject(401)}));
  assert.equal(events.length,0);
  storage.set('mandi-token','current');
  await assert.rejects(api.get('/test',{adapter:reject(403)}));
  assert.equal(storage.get('mandi-token'),'current');
  await assert.rejects(api.get('/test',{adapter:reject(401,()=>storage.set('mandi-token','new-session'))}));
  assert.equal(storage.get('mandi-token'),'new-session');
  assert.equal(events.length,0);
  await assert.rejects(api.get('/test',{adapter:reject(401)}));
  assert.equal(storage.has('mandi-token'),false);
  assert.deepEqual(events,['mandi-session-expired']);
});
