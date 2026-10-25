from __future__ import annotations
import base64,gzip,json
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go

WARM=['#fff6e7','#f5dfc2','#e5bc92','#cf9268','#ac6843','#703c2a']
SCALE=[[i/5,c] for i,c in enumerate(WARM)]
def style(fig,title,height=410):
 fig.update_layout(title={'text':title,'font':{'size':19},'x':.02},height=height,paper_bgcolor='#fffdf9',plot_bgcolor='#fffdf9',font={'family':'Noto Sans CJK SC, Microsoft YaHei, sans-serif','size':12,'color':'#655346'},margin={'l':65,'r':35,'t':70,'b':65},hoverlabel={'bgcolor':'#fff8ec'},legend={'orientation':'h','y':1.1},colorway=WARM[2:])
 fig.update_xaxes(showgrid=False,linecolor='#bdae9c',zeroline=False)
 fig.update_yaxes(gridcolor='#eee2d3',zeroline=False)
 return fig

def trend(records,province='全部'):
 df=pd.DataFrame(records)
 if province!='全部':df=df[df.province==province]
 out=df.groupby('year').agg(total_mt=('total_mt','sum'),coverage=('province','nunique')).reset_index()
 fig=go.Figure(go.Scatter(x=out.year.tolist(),y=out.total_mt.tolist(),mode='lines+markers',line={'color':'#a96642','width':2.5},marker={'size':6},customdata=out.coverage.tolist(),hovertemplate='%{x}年<br>%{y:,.2f} 百万吨<br>有值地区：%{customdata}个<extra></extra>'))
 fig=style(fig,'年度排放量变化' if province=='全部' else province+'的年度变化');fig.update_xaxes(title='年份',tickformat='d');fig.update_yaxes(title='已知地区排放合计 / 百万吨',rangemode='tozero');return fig

def ranking(records,year):
 df=pd.DataFrame(records);r=df[df.year==year].sort_values('total_mt',ascending=False).head(10).sort_values('total_mt')
 fig=go.Figure(go.Bar(x=r.total_mt.tolist(),y=r.province.tolist(),orientation='h',marker_color='#b47b55',text=[f'{v:,.1f}' for v in r.total_mt],textposition='outside',cliponaxis=False,hovertemplate='%{y}<br>%{x:,.2f} 百万吨<extra></extra>'));fig=style(fig,f'{year}年排放量前十位',480);fig.update_xaxes(title='表观排放量 / 百万吨',range=[0,max(r.total_mt.max()*1.2,1)]);return fig

def heatmap(records,analysis):
 df=pd.DataFrame(records);order=[r['province'] for r in analysis['features']];order+= [p for p in analysis['provinces'] if p not in order];p=df.pivot(index='province',columns='year',values='total_mt').reindex(index=order,columns=analysis['years']);z=[[float(v) if pd.notna(v) else None for v in row] for row in p.values]
 fig=go.Figure(go.Heatmap(x=p.columns.tolist(),y=p.index.tolist(),z=z,colorscale=SCALE,zmin=0,hoverongaps=False,colorbar={'title':'百万吨','thickness':13},hovertemplate='%{y} %{x}年<br>%{z:,.2f} 百万吨<extra></extra>'));fig=style(fig,'各省各年的排放量',max(440,150+len(order)*22));fig.update_yaxes(autorange='reversed',showgrid=False);fig.update_xaxes(title='年份',tickformat='d');return fig

def scatter(analysis,growth=10):
 fig=go.Figure();features=[r for r in analysis['features'] if r['growth_pct'] is not None]
 for focus in [False,True]:
  rows=[r for r in features if (r['total_mt']>=analysis['threshold'] and r['growth_pct']>growth)==focus]
  fig.add_trace(go.Scatter(x=[r['total_mt'] for r in rows],y=[r['growth_pct'] for r in rows],text=[r['province'] for r in rows],mode='markers',name='符合条件' if focus else '其他地区',marker={'size':11 if focus else 8,'symbol':'diamond' if focus else 'circle','color':'#703c2a' if focus else '#d5a47e'},hovertemplate='%{text}<br>%{x:,.2f} 百万吨<br>五年变化 %{y:.2f}%<extra></extra>'))
 fig.add_vline(x=analysis['threshold'],line_dash='dash',line_color='#b9a48e',line_width=1);fig.add_hline(y=growth,line_dash='dash',line_color='#b9a48e',line_width=1)
 fig=style(fig,f'{analysis["base"]}—{analysis["latest"]}年变化与末年排放量',440);fig.update_xaxes(title=f'{analysis["latest"]}年排放量 / 百万吨');fig.update_yaxes(title='五年累计变化 / %');return fig

def load_map(root=None):
 root=root or Path(__file__).resolve().parent
 p=root/'data/map.json.gz.b64'
 return json.loads(gzip.decompress(base64.b64decode(p.read_text(encoding='ascii')))) if p.exists() else json.loads((root/'data/map.json').read_text(encoding='utf-8'))

def province_map(records,year,mapdata=None):
 mp=mapdata or load_map();df=pd.DataFrame(records);rows=df[df.year==year];lookup=dict(zip(rows.province,rows.total_mt));maximum=max(float(rows.total_mt.max()),1);shapes=[]
 for region in mp['regions']:
  v=lookup.get(region['name']);color='#d3cec7' if v is None else WARM[min(5,int(v/maximum*5.999))]
  shapes.append({'type':'path','path':region['path'],'fillcolor':color,'line':{'color':'#8d8072','width':.45},'fillrule':'evenodd','layer':'below'})
 shapes.append({'type':'path','path':mp['border'],'line':{'color':'#786552','width':.6},'layer':'above'})
 fig=go.Figure();fig.update_layout(shapes=shapes)
 if all('center' in r for r in mp['regions']):
  fig.add_trace(go.Scatter(x=[r['center'][0] for r in mp['regions']],y=[r['center'][1] for r in mp['regions']],mode='markers',marker={'color':'#a96642','size':5,'opacity':.3},text=[r['name'] for r in mp['regions']],customdata=[f'{lookup[r["name"]]:,.2f} 百万吨' if r['name'] in lookup else '无排放数据' for r in mp['regions']],hovertemplate='%{text}<br>%{customdata}<extra></extra>',showlegend=False))
 # An invisible data trace supplies the same numeric color scale as the shapes.
 fig.add_trace(go.Scatter(x=[-10,-10],y=[-10,-10],mode='markers',marker={'size':.1,'color':[0,maximum],'colorscale':SCALE,'cmin':0,'cmax':maximum,'showscale':True,'colorbar':{'title':'百万吨','len':.65,'thickness':14}},hoverinfo='skip',showlegend=False))
 fig=style(fig,f'{year}年省级排放分布',750);fig.update_layout(margin={'l':0,'r':60,'t':65,'b':70},annotations=[{'text':'灰色为无数据，不表示零。','xref':'paper','yref':'paper','x':0,'y':-.035,'showarrow':False,'xanchor':'left'},{'text':'底图数据包标注审图号：GS(2020)4619号','xref':'paper','yref':'paper','x':0,'y':-.09,'showarrow':False,'xanchor':'left'}]);fig.update_xaxes(range=[0,700],visible=False,constrain='domain');fig.update_yaxes(range=[740,0],visible=False,scaleanchor='x',scaleratio=1);return fig
