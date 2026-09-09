#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Export public language knowledge from the spec, independent of marketing pages."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'reference/language-index.json'
def digest(raw): return hashlib.sha256(raw).hexdigest()
def build(root=ROOT):
    files = [root/'schemas/workflow.schema.json', *sorted((root/'templates').glob('*.nika.yaml'))]
    inputs = {path.relative_to(root).as_posix(): digest(path.read_bytes()) for path in files}
    # Reuse a content-identical pin: a squash merge must not churn all docs.
    previous_path = root / 'reference/language-index.json'
    previous = json.loads(previous_path.read_text()) if previous_path.exists() else {}
    revision = previous.get('revision') if previous.get('inputs') == inputs else None
    if not revision:
        revision = subprocess.check_output(['git','log','-1','--format=%H','--',*inputs],cwd=root,text=True).strip()
    if not re.fullmatch('[a-f0-9]{40}', revision): raise ValueError('Invalid source revision')
    for path in files:
        rel=path.relative_to(root).as_posix(); raw=path.read_bytes()
        committed=subprocess.check_output(['git','show',f'{revision}:{rel}'],cwd=root)
        if committed != raw: raise ValueError(f'Uncommitted source {rel}: commit its owner change before exporting a revision-bound mirror')
    schema=json.loads(files[0].read_text()); words={}
    def walk(value,pointer=''):
        if isinstance(value,dict):
            props=value.get('properties',{})
            for name,decl in props.items():
                if not re.fullmatch(r'[a-z][a-z0-9_]*',name): raise ValueError(f'Unsupported property slug: {name}')
                escape=lambda s:s.replace('~','~0').replace('/','~1')
                words.setdefault(name,[]).append({'pointer':pointer+'/properties/'+escape(name),'context':pointer or '/', 'required':name in value.get('required',[]),'declaration':decl,'siblings':sorted(set(props)-{name})})
            # Only schema-bearing keywords contain declarations. Examples,
            # defaults and const values may themselves contain "properties".
            escape=lambda s:s.replace('~','~0').replace('/','~1')
            for key in ['properties','patternProperties','$defs','definitions','dependentSchemas']:
                for name,child in value.get(key,{}).items():walk(child,pointer+'/'+key+'/'+escape(name))
            for key in ['allOf','anyOf','oneOf','prefixItems']:
                for i,child in enumerate(value.get(key,[])):walk(child,pointer+'/'+key+'/'+str(i))
            for key in ['items','contains','additionalProperties','unevaluatedProperties','unevaluatedItems','propertyNames','not','if','then','else']:
                child=value.get(key)
                if isinstance(child,dict):walk(child,pointer+'/'+key)
    walk(schema)
    records=[]
    for name,contracts in sorted(words.items()):
        examples=[]
        for file in files[1:]:
            lines=file.read_text().splitlines()
            hits=[i for i,line in enumerate(lines) if re.match(r'^\s*'+re.escape(name)+r'\s*:',line)]
            if not hits:continue
            first=hits[0]; start=max(0,first-3); end=min(len(lines),first+7)
            examples.append({'path':file.relative_to(root).as_posix(),'line':first+1,'startLine':start+1,'endLine':end,'excerpt':'\n'.join(lines[start:end]),'matchKind':'literal-key-occurrence'})
        records.append({'id':'language:word:'+name,'name':name,'docsPath':'reference/language/words/'+name,'contracts':contracts,'examples':examples})
    return {'schemaVersion':1,'kind':'spec-language-knowledge','owner':'supernovae-st/nika-spec','revision':revision,'inputs':inputs,'words':records}
def main():
    p=argparse.ArgumentParser();p.add_argument('--write',action='store_true');p.add_argument('--stdout',action='store_true');a=p.parse_args()
    text=json.dumps(build(),ensure_ascii=False,indent=2)+'\n'
    if a.stdout:print(text,end='')
    elif a.write:OUTPUT.write_text(text)
    elif not OUTPUT.exists() or OUTPUT.read_text()!=text:raise SystemExit('Language knowledge drift: run python3 scripts/knowledge-projector.py --write')
    else:print('Language knowledge matches schema and templates')
if __name__=='__main__':main()
