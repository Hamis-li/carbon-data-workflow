from __future__ import annotations
import base64,io,json,zipfile
from pathlib import Path
import pandas as pd
import streamlit as st
from pipeline import process_file,safe_csv,json_safe,COLUMNS,RULES
from charts import trend,ranking,province_map,heatmap,scatter

ROOT=Path(__file__).resolve().parent
st.set_page_config(page_title='碳数工坊 · 数据处理演示',page_icon='▥',layout='wide')
st.markdown('''<style>
.block-container{padding-top:2.5rem;max-width:1320px}h1,h2,h3{font-family:"Noto Serif SC","SimSun",serif!important;font-weight:500!important}h1{font-size:2.1rem!important}h2{font-size:1.55rem!important}h3{font-size:1.2rem!important}[data-testid="stSidebar"]{background:#eee5d8;border-right:1px solid #ded0bf}[data-testid="stMetric"]{padding:16px 18px;border-block:1px solid #dfd0bf}[data-testid="stMetricLabel"]{color:#8b7561}[data-testid="stMetricValue"]{font-family:Georgia,serif;color:#74462e}[data-testid="stFileUploader"]{border:1px dashed #cba581;border-radius:8px;padding:18px;background:#fffaf2}div.stButton>button,div.stDownloadButton>button{border-radius:4px}div.stButton>button[kind="primary"]{background:#a96642}.eyebrow{font-size:11px;letter-spacing:2px;color:#a07b5c;margin-bottom:12px}.muted{color:#8b7868;font-size:13px}.hero-box{background:#eee1cd;padding:24px 26px;border-radius:6px;min-height:236px}.source{font-size:11px;color:#9a8574;border-top:1px solid #e3d5c5;padding-top:18px;margin-top:28px}code{color:#956340!important}hr{border-color:#e1d3c3!important}
</style>''',unsafe_allow_html=True)
STEPS=['01  上传数据','02  清洗检查','03  整理表达','04  结果展示','05  云端与 Docker']
LABELS={'province':'省份','province_code':'省级代码','year':'年份','total_mt':'排放总量（百万吨）','coal_mt':'煤','oil_mt':'石油','gas_mt':'天然气','cement_mt':'水泥','source_sheet':'原工作表','source_row':'原行号','source_column':'原列号','reason':'处理原因','growth_pct':'五年变化（%）','yoy_pct':'同比变化（%）','focus':'符合条件'}
for key,value in [('result',None),('stage',STEPS[0]),('last_error',None)]:
 if key not in st.session_state:st.session_state[key]=value

def sample_bytes():
 path=ROOT/'data/sample.xlsx'
 return path.read_bytes() if path.exists() else base64.b64decode((ROOT/'data/sample.xlsx.b64').read_text(encoding='ascii'))

def run(content,name,unit='mt'):
 try:
  with st.spinner('服务器正在读取、检查并计算，请稍候…'):
   st.session_state.result=process_file(content,name,unit)
  st.session_state.last_error=None;st.session_state.stage=STEPS[1]
 except Exception as exc:st.session_state.last_error=str(exc)

def load_sample():run(sample_bytes(),'中国省级表观碳排放清单（1997-2022）.xlsx')
def load_dirty():run((ROOT/'data/issues-example.csv').read_bytes(),'带问题的演示数据.csv')
def upload():
 f=st.session_state.get('upload_file')
 if f is None:st.session_state.last_error='请先选择文件。';return
 run(f.getvalue(),f.name,'tonnes' if st.session_state.get('input_unit')=='吨二氧化碳' else 'mt')

def change_stage(value):st.session_state.stage=value
def table(records,columns=None,height=None):
 df=pd.DataFrame(records,columns=columns) if not records else pd.DataFrame(records)
 if columns:df=df.reindex(columns=columns)
 cfg={k:st.column_config.NumberColumn(LABELS.get(k,k),format='%d') for k in ['year','province_code','source_row'] if k in df.columns}
 cfg.update({k:st.column_config.NumberColumn(LABELS.get(k,k),format='%.4f') for k in ['total_mt','coal_mt','oil_mt','gas_mt','cement_mt','growth_pct','yoy_pct'] if k in df.columns})
 for k in df.columns:
  if k not in cfg:cfg[k]=st.column_config.Column(LABELS.get(k,k))
 st.dataframe(df,width='stretch',hide_index=True,column_config=cfg,**({'height':height} if height else {}))

def chart(fig,key):
 st.plotly_chart(fig,width='stretch',key=key,config={'displaylogo':False,'toImageButtonOptions':{'format':'svg','filename':key,'height':None,'width':None},'scrollZoom':False})
 st.download_button('下载此图交互页面',fig.to_html(include_plotlyjs=True).encode('utf-8'),file_name=key+'.html',mime='text/html',key='dl-'+key)

with st.sidebar:
 st.markdown('## ▥ 碳数工坊')
 st.caption('DATA TO INSIGHT · 课程演示')
 st.divider()
 choice=st.radio('一份数据的处理旅程',STEPS,key='stage')
 st.caption('按步骤查看，也可以随时返回。')
 st.divider()
 st.markdown('**数据有来源，处理有记录。**')
 st.caption('从上传、清洗、整理，到图表与下载。')
 st.download_button('下载CSV上传模板',(ROOT/'data/template.csv').read_bytes(),'上传模板.csv','text/csv')
 st.markdown('[CEADs数据来源](https://www.ceads.net.cn/data/carbon-inventory/provincial-level/)')
 st.caption('地图底图数据包标注审图号：GS(2020)4619号')

stage=STEPS.index(choice)
st.markdown(f'<div class="eyebrow">PROCESS {stage+1:02d} / 05</div>',unsafe_allow_html=True)
st.title(['从一份表格开始','先看数据，哪里需要处理','把数据整理成统一的样子','让结果更容易看懂','这次怎样算，以后怎样扩展'][stage])
st.caption(['上传Excel或CSV，服务器完成检查、整理与计算，再生成可下载的结果。','每条合并或隔离记录都能查看原因，不悄悄改掉问题值。','一行代表一个省份的一年，名称、年份和单位统一。','图表来自本次处理后的数据，暖色越深表示排放量越大。','当前功能与后续扩展分开说明，不把Docker当作分布式计算。'][stage])
if st.session_state.last_error:st.error(st.session_state.last_error)
result=st.session_state.result

if stage==0:
 left,right=st.columns([1.15,1],gap='large')
 with left:
  st.subheader('把数据带进来')
  st.file_uploader('选择Excel或CSV',type=['xlsx','csv'],key='upload_file',help='最大3MB。支持原CEADs年度清单，或下载模板中的统一字段。')
  st.selectbox('统一格式文件中的排放单位',['百万吨二氧化碳','吨二氧化碳'],key='input_unit',help='原CEADs年度清单自动读取NOTE页的Mt说明，不使用此选择。')
  st.button('开始处理上传数据',type='primary',on_click=upload,width='stretch')
 with right:
  st.markdown('<div class="hero-box"><div class="eyebrow">先试一份真实数据</div><h2>1997—2022<br/>中国省级碳排放清单</h2><p>30个省级地区，26个年份，780条省年记录。示例与自己上传的文件使用同一套处理代码。</p></div>',unsafe_allow_html=True)
  st.button('一键体验示例',on_click=load_sample,type='primary',width='stretch')
  st.button('试试带问题的数据',on_click=load_dirty,width='stretch')
  st.download_button('下载原始示例Excel',sample_bytes(),'中国省级表观碳排放清单（1997-2022）.xlsx')
 st.divider()
 cols=st.columns(3)
 for c,title,text in zip(cols,['支持什么数据','处理后得到什么','文件怎样使用'],['支持.xlsx和UTF-8 CSV。统一表需要province、year、total_mt三个字段；四个分项可选。不支持任意结构的Excel。','整理后的CSV、问题清单、统计表、完整处理记录、五类图表与可离线查看的交互图。','文件上传到运行本程序的服务器计算，不写入长期文件存储。会话结束后请自行保存下载结果。']):
  with c:st.markdown('**'+title+'**');st.caption(text)
 if result:st.success(f'已有处理结果：保留{result["summary"]["kept"]}条记录。可在侧栏继续查看。')
elif not result:
 st.info('还没有处理结果。先上传文件，或点击下方按钮体验示例。')
 st.button('一键体验示例',on_click=load_sample,type='primary')
else:
 records=result['records'];a=result['analysis'];df=pd.DataFrame(records,columns=COLUMNS)
 if stage==1:
  for c,label,value in zip(st.columns(4),['原始提取','本次保留','单独列出','服务器处理时间'],[str(result['summary']['input'])+'条',str(result['summary']['kept'])+'条',str(result['summary']['excluded'])+'条',f'{result["run"]["ms"]:.0f}毫秒']):c.metric(label,value)
  st.subheader('每一步，都有记录')
  for c,s in zip(st.columns(3),result['stages']):
   with c:st.markdown('**✓ '+s['title']+'**');st.write(s['detail']);st.caption(f'本次用时约{s["ms"]:.0f}毫秒')
  l,r=st.columns([1.5,1],gap='large')
  with l:
   st.subheader('具体处理规则')
   for rule in result['rules']:st.markdown('- '+rule)
  with r:
   st.subheader('实际修改计数')
   for k,title in [('renamed','统一省名'),('derived','用四项补齐总量'),('converted','换算单位'),('exact_duplicates','合并完全重复'),('conflicts','隔离冲突记录')]:st.write(f'{title}：**{result["changes"][k]}条**')
   st.caption('同一条可能同时改省名和单位，不能把所有修改计数相加。')
  st.subheader('原始表的样子')
  preview=pd.DataFrame([[str(v) if v is not None else '' for v in row] for row in result['raw_preview']]);st.dataframe(preview,width='stretch',hide_index=True)
  st.subheader('需要注意的记录')
  if result['issues']:table(result['issues'],['province','year','source_sheet','source_row','reason'])
  else:st.success('本次没有发现需要隔离或合并的记录。没有问题也会如实显示为0。')
  st.download_button('下载问题清单CSV',safe_csv(result['issues'],['province','year','source_sheet','source_row','reason']),'问题清单.csv')
 elif stage==2:
  st.markdown('**统一省名 → 整数年份 → 百万吨单位 → 按省份、年份排序**')
  term=st.text_input('搜索省份或年份',placeholder='例如：北京 / 2022')
  shown=df[df.province.str.contains(term,regex=False)|df.year.astype(str).str.contains(term,regex=False)] if term else df
  table(shown.to_dict('records'),COLUMNS,height=430)
  st.caption(f'当前显示{len(shown)}条；完整数据共{len(df)}条。下载按钮提供完整数据，不受搜索限制。')
  st.download_button('下载完整统一格式CSV',safe_csv(records,COLUMNS),'整理后的省年数据.csv',type='primary')
  l,r=st.columns([1.2,1],gap='large')
  with l:
   st.subheader('字段说明')
   table([{'字段':'province / province_code','说明':'中文省名和6位行政代码，与地图对应。'},{'字段':'year','说明':'年份，一省一年保留一条无冲突记录。'},{'字段':'total_mt / 四项分量','说明':'单位均为百万吨二氧化碳；空值不表示零。'},{'字段':'source_sheet / row / column','说明':'原表位置，方便逐条回查。'}])
  with r:
   st.subheader('保留来源信息');st.write('文件：'+result['file']['name']);st.write('格式：'+result['file']['format']);st.write('输出单位：'+result['file']['unit']);st.caption('SHA-256文件摘要，仅用于识别文件是否相同。');st.code(result['file']['sha256'],language=None)
 elif stage==3:
  if not records:st.warning('没有通过检查的记录，请返回问题清单。');st.stop()
  y,p,g=st.columns(3)
  year=y.selectbox('地图和排名年份',a['years'],index=len(a['years'])-1)
  province=p.selectbox('趋势图查看',['全部',*a['provinces']])
  growth=g.selectbox('五年累计增长超过（%）',[5,10,15,20],index=1)
  selected=df[df.year==year];features=pd.DataFrame(a['features']);features['focus']=(features.total_mt>=a['threshold'])&(features.growth_pct>growth)
  focus=features[features.focus]
  for c,label,value in zip(st.columns(4),[f'{year}年已知地区合计','该年有值地区','年份范围','末年符合条件'],[f'{selected.total_mt.sum():,.2f}百万吨',f'{len(selected)}/34',f'{a["years"][0]}—{a["latest"]}',f'{len(focus)}个' if a['base'] else '缺少五年对比']):c.metric(label,value)
  if any(not r['complete'] for r in a['annual']):st.warning('各年地区覆盖不一致。合计只表示各年已知地区相加，不能把变化全部解释为排放变化。')
  st.subheader('01 时间变化');chart(trend(records,province),'01_年度变化')
  st.subheader('02 省级比较');chart(ranking(records,year),'02_省级排名')
  st.subheader('03 地图表达');st.caption('悬停浅色圆点查看省份数据。灰色为无数据，不能当作零。');chart(province_map(records,year),'03_省级地图')
  st.subheader('04 各省各年一起看');chart(heatmap(records,a),'04_时序热力图')
  st.subheader('05 排放较多且增长较快的地区')
  if a['base']:
   st.caption(f'固定比较末年{a["latest"]}与{a["base"]}年；规模下限为末年75%分位数{a["threshold"]:.2f}百万吨，五年增长严格大于{growth}%。这只是历史筛选，不是预测或超标判断。')
   chart(scatter(a,growth),'05_规模与增长');table(focus.to_dict('records'),['province','year','total_mt','growth_pct','yoy_pct'])
  else:st.info('没有距末年整五年的数据，不强行计算五年变化。其余四类图表可以正常使用。')
  st.download_button('下载末年统计结果CSV',safe_csv(features.to_dict('records'),['province','year','total_mt','growth_pct','yoy_pct','focus']),'末年统计.csv')
 elif stage==4:
  st.subheader('当前已经运行的流程')
  st.info('浏览器上传文件 → Streamlit服务器运行Python → 读取与清洗 → 整理成省年表 → 统计计算 → 浏览器显示图表与下载。')
  st.write('当前运行位置取决于启动方式：本地启动就在自己的电脑计算；部署到Streamlit Community Cloud后，同一份Python代码在云端服务器计算。不是浏览器假装完成分析。')
  st.caption(f'本次任务：{result["run"]["id"]} · 时间：{result["run"]["at"]} · 处理约{result["run"]["ms"]:.0f}毫秒。时间仅描述本次运行，不代表大规模性能。')
  left,right=st.columns(2,gap='large')
  with left:
   st.subheader('数据很多以后，再增加这些')
   st.markdown('1. 原文件保存到云端文件存储，记录版本。\n2. 计算任务进入队列，网页查看进度。\n3. 先按年份分批；单机不够时，再用Spark分给多台机器。\n4. 将计算结果写入数据库，便于再次查询。')
   st.caption('以上是后续扩展方案。当前版没有接入长期存储、任务队列或Spark集群。')
  with right:
   st.subheader('Docker负责方便运行')
   st.write('项目附Dockerfile与compose配置，可在有Docker的电脑或服务器构建启动。')
   st.code('docker compose up --build\n# 浏览器打开 http://localhost:8501',language='bash')
   st.caption('当前未向镜像仓库发布镜像。Docker不会自动增加算力，也不能代替大数据计算。')
  st.subheader('保存本次成果')
  package=io.BytesIO()
  with zipfile.ZipFile(package,'w',zipfile.ZIP_DEFLATED) as archive:
   archive.writestr('统一格式数据.csv',safe_csv(records,COLUMNS));archive.writestr('问题清单.csv',safe_csv(result['issues'],['province','year','source_sheet','source_row','reason']));archive.writestr('末年统计.csv',safe_csv(a['features']));archive.writestr('完整处理记录.json',json.dumps(json_safe(result),ensure_ascii=False,indent=2));archive.writestr('数据来源与规则.txt','输入文件：'+result['file']['name']+'\n文件SHA-256：'+result['file']['sha256']+'\n地图：所提供的标准地图矢量数据包，标注审图号GS(2020)4619号。\n\n'+'\n'.join(RULES))
  c1,c2=st.columns(2)
  c1.download_button('下载本次成果包ZIP',package.getvalue(),'数据处理成果.zip','application/zip',type='primary',width='stretch')
  c2.download_button('下载完整处理记录JSON',json.dumps(json_safe(result),ensure_ascii=False,indent=2).encode('utf-8'),'处理记录.json','application/json',width='stretch')
  st.caption('文件≤3MB，输入≤50,000条，Excel解压后≤32MB。仅支持指定省级碳排放结构。上传文件保留在当前会话内存中，不写入长期存储。')
 st.divider()
 if stage<4:st.button('下一步：'+STEPS[stage+1][4:],on_click=change_stage,args=(STEPS[stage+1],),type='primary')
st.markdown('<div class="source">数据：CEADs中国省级表观碳排放清单（1997—2022）。地图：所提供的34省矢量边界及国界线，数据包标注审图号GS(2020)4619号。演示版不代表未来预测或排放效率评价。</div>',unsafe_allow_html=True)
