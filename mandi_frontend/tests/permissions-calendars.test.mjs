import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import ts from 'typescript';
import {createElement} from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import DateObjectModule from 'react-date-object';
const DateObject=DateObjectModule.default??DateObjectModule;
import gregorian from 'react-date-object/calendars/gregorian.js';
import arabic from 'react-date-object/calendars/arabic.js';
import persian from 'react-date-object/calendars/persian.js';
import gregorian_en from 'react-date-object/locales/gregorian_en.js';
const root=path.resolve(import.meta.dirname,'..');
const out=path.join(root,'node_modules/.cache/mandi-tests');await fs.mkdir(out,{recursive:true});
async function compile(source,name,replacements={}){let text=await fs.readFile(path.join(root,'src',source),'utf8');for(const [from,to]of Object.entries(replacements))text=text.replaceAll(from,to);const js=ts.transpileModule(text,{compilerOptions:{module:ts.ModuleKind.ESNext,jsx:ts.JsxEmit.ReactJSX,target:ts.ScriptTarget.ES2023}}).outputText;await fs.writeFile(path.join(out,name+'.mjs'),js);return import(path.join(out,name+'.mjs'));}
const {SessionContext}=await compile('lib/session.ts','session');
const {Can,CanAny}=await compile('components/Can.tsx','Can',{'@/lib/session':'./session.mjs'});
await compile('lib/calenders.tsx','calenders',{'react-date-object/calendars/persian':'react-date-object/calendars/persian.js','react-date-object/calendars/arabic':'react-date-object/calendars/arabic.js','react-date-object/calendars/gregorian':'react-date-object/calendars/gregorian.js','react-date-object/locales/persian_fa':'react-date-object/locales/persian_fa.js','react-date-object/locales/arabic_ar':'react-date-object/locales/arabic_ar.js','react-date-object/locales/gregorian_en':'react-date-object/locales/gregorian_en.js'});
const {formatSmartDate}=await compile('utils/formatSmartDate.ts','formatSmartDate',{'@/lib/calenders':'./calenders.mjs','react-date-object/calendars/persian':'react-date-object/calendars/persian.js','react-date-object/calendars/arabic':'react-date-object/calendars/arabic.js','react-date-object/calendars/gregorian':'react-date-object/calendars/gregorian.js','react-date-object/locales/arabic_ar':'react-date-object/locales/arabic_ar.js','react-date-object/locales/gregorian_en':'react-date-object/locales/gregorian_en.js'});
const digits=s=>s.replace(/[۰-۹٠-٩]/g,d=>String('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩'.indexOf(d)%10));
function render(props,permissions=[],staff=false,Component=Can){return renderToStaticMarkup(createElement(SessionContext.Provider,{value:{user:{is_staff:staff},permissions}},createElement(Component,{fallback:'denied',...props},'allowed')));}
test('Can checks individual, OR, AND, missing permissions and staff restriction',()=>{assert.equal(render({permission:'a'},['a']),'allowed');assert.equal(render({permission:'a'},[]),'denied');assert.equal(render({permissions:['a','b']},['b']),'allowed');assert.equal(render({permissions:['a','b'],operator:'and'},['a']),'denied');assert.equal(render({permissions:['a','b'],operator:'and'},['a','b']),'allowed');assert.equal(render({permission:'a',staffOnly:true},['a']),'denied');assert.equal(render({permission:'a',staffOnly:true},['a'],true),'allowed');assert.equal(render({},['a']),'denied');assert.equal(render({permissions:['b']},['a'],false,CanAny),'denied');});
test('stored Gregorian dates display correctly across a Shamsi leap-year boundary',()=>{assert.equal(digits(formatSmartDate({date:'2024-03-20',calendarType:'shamsi'})),'1403/01/01');assert.equal(digits(formatSmartDate({date:'2024-02-29',calendarType:'shamsi'})),'1402/12/10');assert.equal(formatSmartDate({date:'2026-11-07',calendarType:'gregorian'}),'2026/11/07');});
test('Qamari and Shamsi date selections round-trip to the original Gregorian API date',()=>{for(const raw of ['2024-02-29','2024-03-20','2026-11-07','2026-12-31'])for(const calendar of [arabic,persian]){const date=new DateObject({date:raw,format:'YYYY-MM-DD',calendar:gregorian,locale:gregorian_en});date.convert(calendar);assert.notEqual(date.year,Number(raw.slice(0,4)));assert.equal(date.convert(gregorian,gregorian_en).format('YYYY-MM-DD'),raw);}});
