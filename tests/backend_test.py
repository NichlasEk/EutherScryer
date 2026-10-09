import importlib.util
import json
import pathlib
import tempfile
import unittest
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('scryer',pathlib.Path(__file__).parents[1]/'backend/scryer.py')
scryer=importlib.util.module_from_spec(spec);spec.loader.exec_module(scryer)

class BackendTest(unittest.TestCase):
    def fixture(self):
        return {'nodes':[{'id':'server','type':'host','status':'online','detail':'SECRET'}, {'id':'books','type':'service','status':'running','token':'SECRET'}, {'id':'private','type':'vault-content','status':'online'}], 'edges':[{'from':'server','to':'books','type':'hosts','label':'SECRET'}, {'from':'server','to':'private','type':'hosts'}]}
    def test_context_is_allowlisted(self):
        ctx=scryer.context(self.fixture(),'server')
        self.assertNotIn('SECRET',json.dumps(ctx));self.assertNotIn('private',json.dumps(ctx));self.assertEqual(len(ctx['nodes']),2)
        self.assertEqual(scryer.context(self.fixture(),'missing')['nodes'],[])
    def test_disabled_model_never_connects(self):
        with patch.object(scryer.urllib.request,'urlopen') as call:
            result=scryer.answer({}, {'question':'hello','node':'server'},self.fixture())
            self.assertEqual(result['source'],'scryer-inventory');call.assert_not_called()
    def test_model_budget_context_and_durable_cooldown(self):
        with tempfile.TemporaryDirectory() as directory:
            config={'server':{'state_root':directory},'ai':{'enabled':True,'endpoint':'http://localhost:11434','model':'test'}}
            with patch.object(scryer.urllib.request,'urlopen') as call:
                call.return_value.__enter__.return_value.read.return_value=b'{"response":"A tentative idea"}'
                first=scryer.answer(config,{'question':'What if?','node':'server'},self.fixture())
                second=scryer.answer(config,{'question':'again','node':'server'},self.fixture())
                self.assertEqual(first['source'],'scryer-model');self.assertEqual(second['source'],'scryer-inventory');self.assertEqual(call.call_count,1)
                body=json.loads(call.call_args.args[0].data)
                self.assertEqual(body['options']['num_predict'],384);self.assertNotIn('SECRET',body['prompt']);self.assertNotIn('tools',body)
    def test_invalid_request_and_failure_are_bounded(self):
        self.assertFalse(scryer.answer({}, {'question':'x'*1201},self.fixture())['ok'])
        self.assertFalse(scryer.answer({}, {'question':'hi','node':'../../secret'},self.fixture())['ok'])
if __name__=='__main__':unittest.main()
