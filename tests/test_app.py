from pathlib import Path
from streamlit.testing.v1 import AppTest
ROOT=Path(__file__).resolve().parents[1]
def test_demo_navigation():
 at=AppTest.from_file(str(ROOT/'app.py'),default_timeout=30).run()
 assert not at.exception
 [b for b in at.button if b.label=='一键体验示例'][0].click().run()
 assert not at.exception
 assert at.session_state['result']['summary']['kept']==780
 for stage in ['03  整理表达','04  结果展示','05  云端与 Docker']:
  at.sidebar.radio[0].set_value(stage).run()
  assert not at.exception,[e.message for e in at.exception]
 return True
if __name__=='__main__':print('App navigation:',test_demo_navigation())
