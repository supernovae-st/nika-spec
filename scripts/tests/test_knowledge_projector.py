# SPDX-License-Identifier: Apache-2.0
import importlib.util,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('projector',ROOT/'scripts/knowledge-projector.py');projector=importlib.util.module_from_spec(spec);spec.loader.exec_module(projector)
class ProjectionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        for d in ['schemas','templates','reference']:(self.root/d).mkdir()
        (self.root/'schemas/workflow.schema.json').write_text(json.dumps({'properties':{'after':{'type':'object'}},'$defs':{'task':{'properties':{'after':{'type':'string'}},'required':['after']}}}))
        (self.root/'templates/example.nika.yaml').write_text('tasks:\n  first:\n    after: previous\n')
    def tearDown(self):self.temp.cleanup()
    def git(self,args,**kwargs):
        if args[1]=='log':return 'b'*40+'\n'
        return (self.root/args[2].split(':',1)[1]).read_bytes()
    def test_scopes_and_requirement_are_distinct(self):
        with patch.object(projector.subprocess,'check_output',side_effect=self.git):data=projector.build(self.root)
        self.assertEqual(len(data['words']),1);contracts=data['words'][0]['contracts']
        self.assertEqual([c['required'] for c in contracts],[False,True]);self.assertEqual(data['words'][0]['examples'][0]['line'],3)
    def test_squash_or_unrelated_commit_preserves_content_pin(self):
        with patch.object(projector.subprocess,'check_output',side_effect=self.git):data=projector.build(self.root)
        data['revision']='a'*40;(self.root/'reference/language-index.json').write_text(json.dumps(data))
        with patch.object(projector.subprocess,'check_output',side_effect=self.git):self.assertEqual(projector.build(self.root)['revision'],'a'*40)
    def test_new_property_changes_projection_and_selects_new_pin(self):
        with patch.object(projector.subprocess,'check_output',side_effect=self.git):data=projector.build(self.root)
        data['revision']='a'*40;(self.root/'reference/language-index.json').write_text(json.dumps(data))
        (self.root/'schemas/workflow.schema.json').write_text('{"properties":{"new_field":{"type":"boolean"}}}')
        with patch.object(projector.subprocess,'check_output',side_effect=self.git):updated=projector.build(self.root)
        self.assertEqual(updated['revision'],'b'*40);self.assertEqual(updated['words'][0]['id'],'language:word:new_field')
    def test_uncommitted_source_not_misrepresented_as_pinned(self):
        def dirty(args,**kwargs):return 'b'*40+'\n' if args[1]=='log' else b'wrong bytes'
        with patch.object(projector.subprocess,'check_output',side_effect=dirty):
            with self.assertRaisesRegex(ValueError,'Uncommitted source'):projector.build(self.root)
    def test_payload_properties_are_not_language_declarations(self):
        schema={'properties':{'real':{'type':'object','default':{'properties':{'fake':{}}},'examples':[{'properties':{'phantom':{}}}]}},'allOf':[{'properties':{'conditional':{'type':'boolean'}}}]}
        (self.root/'schemas/workflow.schema.json').write_text(json.dumps(schema))
        with patch.object(projector.subprocess,'check_output',side_effect=self.git):data=projector.build(self.root)
        self.assertEqual([w['name'] for w in data['words']],['conditional','real'])
if __name__=='__main__':unittest.main()
