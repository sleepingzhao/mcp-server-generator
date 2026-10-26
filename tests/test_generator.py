import ast
import json
import unittest
from generator import SpecError, generate_project, validate_spec
SAMPLE={"name":"Demo Server","package":"demo_server","transport":"stdio","tools":[{"name":"hello","handler":"static","params":[{"name":"name","type":"string","required":True}],"config":{"response":{"message":"Hello {name}"}}},{"name":"get-user","handler":"http","params":[{"name":"id","type":"integer","required":True}],"config":{"method":"GET","url":"https://example.com/users/{id}","headers":"{\"Accept\":\"application/json\"}"}},{"name":"echo","handler":"command","params":[{"name":"text","type":"string","required":True}],"config":{"executable":"echo","args":"[\"{text}\"]"}}]}
class Tests(unittest.TestCase):
 def test_project(self):
  p=generate_project(SAMPLE); self.assertEqual(p.slug,"demo-server"); ast.parse(p.files["server.py"]); json.loads(p.files["server-spec.json"]); self.assertIn("@mcp.tool(name='get-user')",p.files["server.py"])
 def test_duplicate(self):
  s=dict(SAMPLE);s["tools"]=[SAMPLE["tools"][0],SAMPLE["tools"][0]]
  with self.assertRaisesRegex(SpecError,"重复"):validate_spec(s)
 def test_bad_command_args(self):
  s=dict(SAMPLE);s["tools"]=[{"name":"bad","handler":"command","config":{"executable":"echo","args":"oops"}}]
  with self.assertRaisesRegex(SpecError,"JSON"):validate_spec(s)
 def test_extended_http_and_command_config(self):
  s=dict(SAMPLE);s["tools"]=[
   {"name":"api","handler":"http","config":{"method":"POST","url":"https://example.com/{id}","query":{"lang":"{lang}"},"headers":{"Authorization":"Bearer ${ENV:TOKEN}"},"body":{"q":"{q}"},"params_mode":"none","response_mode":"json","timeout":12}},
   {"name":"cmd","handler":"command","config":{"executable":"python","args":["-V"],"cwd":"{folder}","env":{"MODE":"{mode}"},"stdin":"{input}","allowed_exit_codes":[0,2],"timeout":5}}]
  p=generate_project(s); source=p.files["server.py"]; ast.parse(source)
  self.assertIn("response_mode",source); self.assertIn("allowed_exit_codes",source); self.assertIn("ENV:",source)
if __name__=="__main__":unittest.main()
