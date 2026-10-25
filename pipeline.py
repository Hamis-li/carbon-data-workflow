"""Shared server-side pipeline for Streamlit, tests and Docker."""
from __future__ import annotations
import csv,hashlib,io,json,math,time,uuid,zipfile
from datetime import datetime,timezone
import pandas as pd
import openpyxl

MAX_BYTES=3*1024*1024
MAX_ROWS=50000
MAX_UNZIPPED=32*1024*1024
PROVINCES='北京 天津 河北 山西 内蒙古 辽宁 吉林 黑龙江 上海 江苏 浙江 安徽 福建 江西 山东 河南 湖北 湖南 广东 广西 海南 重庆 四川 贵州 云南 陕西 甘肃 青海 宁夏 新疆 西藏 台湾 香港 澳门'.split()
ENGLISH=['Beijing','Tianjin','Hebei','Shanxi','Inner mongolia','Liaoning','Jilin','Heilongjiang','Shanghai','Jiangsu','Zhejiang','Anhui','Fujian','Jiangxi','Shandong','Henan','Hubei','Hunan','Guangdong','Guangxi','Hainan','Chongqing','Sichuan','Guizhou','Yunnan','Shaanxi','Gansu','Qinghai','Ningxia','Xinjiang','Tibet','Taiwan','Hong Kong','Macao']
CODES=[110000,120000,130000,140000,150000,210000,220000,230000,310000,320000,330000,340000,350000,360000,370000,410000,420000,430000,440000,450000,460000,500000,510000,520000,530000,610000,620000,630000,640000,650000,540000,710000,810000,820000]
CODE_MAP=dict(zip(PROVINCES,CODES));EN_MAP={a.lower():b for a,b in zip(ENGLISH,PROVINCES)}
EN_MAP.update({'xizang':'西藏','hongkong':'香港','macau':'澳门'})
PARTS=['coal_mt','oil_mt','gas_mt','cement_mt'];NUMERIC=['total_mt',*PARTS]
COLUMNS=['province','province_code','year',*NUMERIC,'source_sheet','source_row','source_column']
ALIASES={'province':['province','province_cn','省份','省名','地区'],'year':['year','年份','年'],'total_mt':['total_mt','emission_mt','排放总量（百万吨）','排放量（百万吨）','total','排放总量'],'coal_mt':['coal_mt','煤排放量'],'oil_mt':['oil_mt','石油排放量'],'gas_mt':['gas_mt','天然气排放量'],'cement_mt':['cement_mt','水泥排放量']}
RULES=['CEADs年度清单只读取第2—6行，第8行后的能源收支明细不重复相加。','统一省名、行政代码、整数年份与百万吨二氧化碳单位。','总量为空但四个分项齐全时，用四项之和补齐并记入修改记录；其他缺失不填0。','完全相同的重复记录只保留一条；同省同年数值冲突则整组隔离。','不能识别的省名、无效年份、负排放、分项不平衡记录单独列出原因。','没有前一年或五年前的正值时，不计算相应增长率；地图缺测保持为空。']

def province_name(value):
 text=str(value or '').strip()
 if text.lower() in EN_MAP:return EN_MAP[text.lower()]
 for suffix in ['维吾尔自治区','壮族自治区','回族自治区','特别行政区','自治区','省','市']:
  if text.endswith(suffix):text=text[:-len(suffix)];break
 return text if text in PROVINCES else None

def number(value):
 if value is None or str(value).strip().lower() in ['', '-', '—','–','na','n/a','null','nan']:return None
 if isinstance(value,bool):return float('nan')
 try:return float(str(value).replace(',','').replace('，','').replace(' ',''))
 except (TypeError,ValueError):return float('nan')

def tabular_rows(table,sheet):
 if len(table)<2:raise ValueError('文件没有数据记录。')
 header=[str(v or '').strip().lower() for v in table[0]];mapping={}
 for key,options in ALIASES.items():
  matches=[i for i,h in enumerate(header) if h in options]
  if len(matches)>1:raise ValueError(f'{key}存在多个候选列，请只保留一列。')
  if matches:mapping[key]=matches[0]
 if not all(k in mapping for k in ['province','year','total_mt']):raise ValueError('表头未识别，需要province、year、total_mt。请下载模板后整理。')
 records=[]
 for i,row in enumerate(table[1:],2):
  if not any(v is not None and str(v).strip() for v in row):continue
  records.append({**{key:row[col] if col<len(row) else None for key,col in mapping.items()},'source_sheet':sheet,'source_row':i,'source_column':None})
  if len(records)>MAX_ROWS:raise ValueError('输入超过50,000条，请分批上传。')
 return records

def read_source(content:bytes,filename:str,unit='mt'):
 if len(content)>MAX_BYTES:raise ValueError('文件超过3MB，请分批上传。')
 if filename.lower().endswith('.csv'):
  try:text=content.decode('utf-8-sig')
  except UnicodeDecodeError:raise ValueError('CSV请保存为UTF-8编码后上传。')
  try:
   table=[]
   for row in csv.reader(io.StringIO(text),strict=True):
    table.append(row)
    if len(table)>MAX_ROWS+1:raise ValueError('输入超过50,000条，请分批上传。')
  except csv.Error:raise ValueError('CSV引号或分隔符不正确。')
  return tabular_rows(table,'CSV'),'统一字段CSV',[r[:8] for r in table[:9]],unit
 if not filename.lower().endswith('.xlsx'):raise ValueError('仅支持.xlsx与UTF-8编码的.csv。')
 try:
  with zipfile.ZipFile(io.BytesIO(content)) as archive:
   if len(archive.infolist())>1000 or sum(a.file_size for a in archive.infolist())>MAX_UNZIPPED:raise ValueError('Excel解压后过大，请精简文件或分批上传。')
 except zipfile.BadZipFile:raise ValueError('Excel文件不完整，或不是.xlsx格式。')
 workbook=openpyxl.load_workbook(io.BytesIO(content),read_only=True,data_only=True)
 try:
  years=[s for s in workbook.sheetnames if len(s)==4 and s.isdigit()]
  if years and province_name(workbook[years[0]].cell(1,3).value):
   notes=' '.join(str(v) for row in workbook['NOTE'].values for v in row) if 'NOTE' in workbook else ''
   if 'Mt' not in notes and '百万吨' not in notes:raise ValueError('年度清单没有找到Mt单位说明，无法确认单位。')
   records=[];preview=[]
   for name in sorted(years):
    sheet=workbook[name]
    # Reading the six needed rows once avoids repeated streaming reads.
    top=list(sheet.iter_rows(min_row=1,max_row=8,max_col=min(sheet.max_column,100),values_only=True))
    if 'Total apparent CO2 emissions' not in str(top[5][0]):raise ValueError(f'{name}年总量行与模板不符，请核对第6行。')
    for c in range(2,len(top[0])):
     if top[0][c] is None or not str(top[0][c]).strip():continue
     vals={k:top[r][c] for k,r in zip(PARTS,[1,2,3,4])}
     records.append({'province':top[0][c],'year':name,'total_mt':top[5][c],**vals,'source_sheet':name,'source_row':6,'source_column':openpyxl.utils.get_column_letter(c+1)})
    if not preview:preview=[list(r[:8]) for r in top]
   if len(records)>MAX_ROWS:raise ValueError('记录超过50,000条。')
   return records,'CEADs省级年度清单',preview,'mt'
  sheet=workbook[workbook.sheetnames[0]]
  if sheet.max_row>MAX_ROWS+1 or sheet.max_column>100:raise ValueError('表格超过50,000条或100列，请分批整理。')
  table=list(sheet.values)
  return tabular_rows(table,sheet.title),'统一字段Excel',[list(r[:8]) for r in table[:9]],unit
 finally:workbook.close()

def clean_records(raw,unit='mt'):
 if unit not in ['mt','tonnes']:raise ValueError('请选择有效排放单位。')
 factor=1e-6 if unit=='tonnes' else 1;groups={};issues=[];changes={'renamed':0,'derived':0,'converted':0,'exact_duplicates':0,'conflicts':0}
 def issue(r,reason):issues.append({'province':str(r.get('province') or ''),'year':str(r.get('year') or ''),'source_sheet':r.get('source_sheet',''),'source_row':r.get('source_row'),'reason':reason})
 for r in raw:
  province=province_name(r.get('province'))
  if not province:issue(r,'省名无法对应34个省级地区');continue
  year=number(r.get('year'))
  if year is None or not math.isfinite(year) or year!=int(year) or not 1900<=year<=2100:issue(r,'年份不是1900—2100之间的整数');continue
  vals={k:number(r.get(k)) for k in NUMERIC}
  if any(v is not None and (not math.isfinite(v) or v<0) for v in vals.values()):issue(r,'排放量含无效数字或负数');continue
  complete=all(vals[k] is not None for k in PARTS)
  if vals['total_mt'] is None:
   if complete:vals['total_mt']=sum(vals[k] for k in PARTS);changes['derived']+=1
   else:issue(r,'总量缺失且分项不完整，未填0');continue
  if complete and abs(sum(vals[k] for k in PARTS)-vals['total_mt'])>max(1e-6,vals['total_mt']*1e-6):issue(r,'四项之和与总量不一致');continue
  if str(r.get('province')).strip()!=province:changes['renamed']+=1
  if factor!=1:changes['converted']+=1
  item={'province':province,'province_code':CODE_MAP[province],'year':int(year),**{k:v*factor if v is not None else None for k,v in vals.items()},**{k:r.get(k) for k in ['source_sheet','source_row','source_column']}}
  groups.setdefault((province,int(year)),[]).append(item)
 records=[]
 for group in groups.values():
  if any(any(r[k]!=group[0][k] for k in NUMERIC) for r in group[1:]):
   changes['conflicts']+=len(group)
   for r in group:issue(r,'同省同年数值冲突，整组隔离')
  else:
   records.append(group[0]);changes['exact_duplicates']+=len(group)-1
   for r in group[1:]:issue(r,'完全重复，保留一条')
 records.sort(key=lambda r:(r['province_code'],r['year']))
 return records,issues,changes

def analyse(records):
 if not records:return {'years':[],'provinces':[],'annual':[],'features':[],'latest':None,'base':None,'threshold':None,'missing_regions':PROVINCES}
 df=pd.DataFrame(records);years=sorted(df.year.unique().tolist());provinces=list(df.province.unique());latest=int(years[-1]);base=latest-5 if latest-5 in years else None
 lookup={(r['province'],r['year']):r for r in records};annual=[]
 for year in years:
  rows=df[df.year==year];annual.append({'year':int(year),'total_mt':float(rows.total_mt.sum()),'coverage':len(rows),'complete':len(rows)==len(provinces)})
 recent=df[df.year==latest];threshold=float(recent.total_mt.quantile(.75));features=[]
 for r in recent.to_dict('records'):
  before=lookup.get((r['province'],base));prev=lookup.get((r['province'],latest-1))
  growth=(r['total_mt']/before['total_mt']-1)*100 if before and before['total_mt']>0 else None
  yoy=(r['total_mt']/prev['total_mt']-1)*100 if prev and prev['total_mt']>0 else None
  features.append({**r,'growth_pct':growth,'yoy_pct':yoy,'focus':bool(growth is not None and r['total_mt']>=threshold and growth>10)})
 features.sort(key=lambda r:-r['total_mt'])
 return {'years':[int(y) for y in years],'provinces':provinces,'annual':annual,'features':features,'latest':latest,'base':base,'threshold':threshold,'missing_regions':[p for p in PROVINCES if p not in recent.province.tolist()]}

def process_file(content:bytes,filename:str,unit='mt'):
 start=time.perf_counter();raw,kind,preview,actual_unit=read_source(content,filename,unit);read_end=time.perf_counter();records,issues,changes=clean_records(raw,actual_unit);clean_end=time.perf_counter();analysis=analyse(records);end=time.perf_counter()
 if not raw:raise ValueError('没有读取到数据记录。')
 return {'file':{'name':filename,'bytes':len(content),'sha256':hashlib.sha256(content).hexdigest(),'format':kind,'input_unit':actual_unit,'unit':'百万吨二氧化碳'},'raw_preview':preview,'raw_records':raw[:30],'records':records,'issues':issues,'changes':changes,'summary':{'input':len(raw),'kept':len(records),'excluded':len(issues)},'analysis':analysis,'rules':RULES,'run':{'id':str(uuid.uuid4()),'at':datetime.now(timezone.utc).isoformat(),'ms':(end-start)*1000,'runtime':'Python服务器计算','persistent':False},'stages':[{'title':'收集与读取','ms':(read_end-start)*1000,'detail':f'读取{kind}，提取{len(raw)}条原始记录。'},{'title':'清洗并统一格式','ms':(clean_end-read_end)*1000,'detail':f'保留{len(records)}条，单独列出{len(issues)}条原因；统一省名、年份和单位。'},{'title':'统计计算','ms':(end-clean_end)*1000,'detail':'完成年度汇总、末年排名、增长与条件筛选。'}]}

def safe_csv(rows,columns=None):
 df=pd.DataFrame(rows,columns=columns) if not rows else pd.DataFrame(rows)
 if columns:df=df.reindex(columns=columns)
 for col in df.select_dtypes(include=['object','string']).columns:
  df[col]=df[col].map(lambda x:"'"+x if isinstance(x,str) and x.startswith(('=','+','-','@')) else x)
 return df.to_csv(index=False).encode('utf-8-sig')

def json_safe(value):
 if isinstance(value,dict):return {k:json_safe(v) for k,v in value.items()}
 if isinstance(value,list):return [json_safe(v) for v in value]
 if isinstance(value,float) and not math.isfinite(value):return None
 return value
