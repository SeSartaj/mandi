import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import ts from 'typescript';
import {createElement} from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import i18next from 'i18next';
import {initReactI18next} from 'react-i18next';

const root = path.resolve(import.meta.dirname, '..');
const out = path.join(root, 'node_modules/.cache/mandi-control-tests');
await fs.mkdir(out, {recursive:true});
async function compile(source, name, replacements={}) {
  let content = await fs.readFile(path.join(root,'src',source),'utf8');
  for (const [from,to] of Object.entries(replacements)) content = content.replaceAll(from,to);
  const js = ts.transpileModule(content,{compilerOptions:{module:ts.ModuleKind.ESNext,jsx:ts.JsxEmit.ReactJSX,target:ts.ScriptTarget.ES2023}}).outputText;
  const file = path.join(out,`${name}.mjs`);
  await fs.writeFile(file,js);
  return import(file);
}
await i18next.use(initReactI18next).init({lng:'en',resources:{en:{translation:{}},fa:{translation:{Save:'ذخیره',Delete:'حذف'}}}});
await compile('lib/utils.ts','utils');
await compile('components/ui/button.tsx','button',{'@/lib/utils':'./utils.mjs'});
const {FieldSupport} = await compile('components/ui/field-support.tsx','support',{'@/lib/utils':'./utils.mjs'});
const {Input} = await compile('components/ui/input.tsx','input',{'@/lib/utils':'./utils.mjs'});
await compile('components/ui/label.tsx','label',{'@/lib/utils':'./utils.mjs'});
const {FormField} = await compile('components/FormField.tsx','field',{
  '@/components/ui/field-support':'./support.mjs',
  '@/components/ui/input':'./input.mjs',
  '@/components/ui/label':'./label.mjs',
  '@/lib/utils':'./utils.mjs',
});
const buttons = await compile('components/public/ActionButton.tsx','actions',{'@/components/ui/button':'./button.mjs','@/lib/utils':'./utils.mjs'});
const render = (Component,props={},children) => renderToStaticMarkup(createElement(Component,props,children));

test('semantic defaults use submit only for save and never submit for create/edit/cancel/delete',()=>{
  for(const [name,action] of [['CreateButton','create'],['EditButton','edit'],['CancelButton','cancel'],['DeleteButton','delete']]){
    const html=render(buttons[name]);
    assert.match(html,/type="button"/);
    assert.match(html,new RegExp(`data-action="${action}"`));
    assert.match(html,/<svg[^>]*aria-hidden="true"/);
  }
  assert.match(render(buttons.SaveButton),/type="submit"/);
  assert.match(render(buttons.SaveButton,{type:'button'}),/type="button"/);
});

test('every action supports icon-only and icon/text displays with primary or secondary emphasis',()=>{
  for(const action of ['create','edit','save','cancel','delete'])for(const variant of ['primary','secondary']){
    const html=render(buttons.ActionButton,{action,variant,iconOnly:true,label:'Specific record action'});
    assert.match(html,/aria-label="Specific record action"/);
    assert.match(html,/title="Specific record action"/);
    assert.match(html,new RegExp(`data-emphasis="${variant}"`));
    assert.doesNotMatch(html,/<span>/);
    const withText=render(buttons.ActionButton,{action,variant,label:'Specific record action'});
    assert.match(withText,/<span>Specific record action<\/span>/);
  }
  assert.match(render(buttons.DeleteButton),/bg-destructive/);
  assert.match(render(buttons.DiscardButton,{variant:'primary'}),/bg-destructive/);
  assert.match(render(buttons.DeleteButton,{variant:'secondary'}),/text-destructive/);
});

test('loading actions are busy, disabled and retain an accessible name and one icon',()=>{
  const html=render(buttons.SaveButton,{loading:true,iconOnly:true});
  assert.match(html,/aria-busy="true"/);
  assert.match(html,/disabled=""/);
  assert.match(html,/aria-label="Saving…"/);
  assert.equal((html.match(/<svg/g)||[]).length,1);
  assert.match(html,/animate-spin/);
});

test('semantic labels follow the active locale',async()=>{
  await i18next.changeLanguage('fa');
  assert.match(render(buttons.SaveButton),/ذخیره/);
  assert.match(render(buttons.DeleteButton,{iconOnly:true}),/aria-label="حذف"/);
  await i18next.changeLanguage('en');
});

test('empty, help and error states always render the same support slot; errors replace help',()=>{
  for(const props of [{},{description:'Helpful guidance'},{description:'Helpful guidance',error:'Required'}]){
    const html=render(FieldSupport,props);
    assert.match(html,/data-slot="field-support"/);
    assert.match(html,/class="field-support /);
    if(props.error){assert.match(html,/role="alert"/);assert.doesNotMatch(html,/Helpful guidance/);}
    else assert.doesNotMatch(html,/role="alert"/);
  }
  assert.match(render(FieldSupport),/aria-hidden="true"/);
});

test('email and password inputs are semantic and always LTR',()=>{
  for(const type of ['email','password','tel','url']){
    const html=render(Input,{type,dir:'rtl'});
    assert.match(html,/dir="ltr"/);
    assert.match(html,/autocapitalize="none"/i);
    assert.match(html,/autocorrect="off"/i);
    assert.match(html,/spellcheck="false"/i);
  }
  assert.match(render(Input,{type:'email'}),/inputmode="email"/i);
  assert.match(render(Input,{type:'tel'}),/inputmode="tel"/i);
  assert.match(render(Input,{type:'text',dir:'rtl'}),/dir="rtl"/);
});

test('shared fields describe the visible message and retain the slot even when opt-out is passed',()=>{
  const html=render(FormField,{id:'province',label:'Province',description:'Help',error:'Required',reserveErrorSpace:false},createElement('input'));
  assert.match(html,/aria-describedby="province-error"/);
  assert.doesNotMatch(html,/aria-describedby="[^"]*province-description/);
  assert.match(html,/id="province-error"/);
  assert.match(html,/Required/);
  assert.doesNotMatch(html,/>Help</);
  assert.match(render(FormField,{label:'Province',reserveErrorSpace:false},createElement('input')),/data-slot="field-support"/);
});
