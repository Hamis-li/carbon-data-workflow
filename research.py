"""Paired-year attribution and explicit controlled quality experiments."""
from __future__ import annotations
import pandas as pd
from pipeline import PARTS, clean_records

LABELS=dict(zip(PARTS,['煤','石油','天然气','水泥']))

def compare(records: list[dict], start: int, end: int) -> dict:
    df=pd.DataFrame(records)
    left=df[df.year==start].set_index('province')
    right=df[df.year==end].set_index('province')
    names=left.index.intersection(right.index)
    if start>=end or names.empty:
        return {'regions':[], 'sources':[], 'coverage':0}
    rows=[]
    for name in names:
        a,b=left.loc[name],right.loc[name]
        delta=float(b.total_mt-a.total_mt)
        rows.append({'省份':name,'起年总量':float(a.total_mt),'末年总量':float(b.total_mt),'增加量':delta,'累计增长率':float((b.total_mt/a.total_mt-1)*100) if a.total_mt>0 else None})
    rows.sort(key=lambda r:-r['增加量'])
    positive=sum(max(0,r['增加量']) for r in rows)
    negative=sum(min(0,r['增加量']) for r in rows)
    sources=[]
    # Never silently sum incomplete component data as zero.
    for key,label in LABELS.items():
        complete=left.loc[names,key].notna().all() and right.loc[names,key].notna().all()
        sources.append({'来源':label,'增加量':float(right.loc[names,key].sum()-left.loc[names,key].sum()) if complete else None})
    q=float(right.loc[names,'total_mt'].quantile(.75))
    focus=[r['省份'] for r in rows if r['末年总量']>=q and r['累计增长率'] is not None and r['累计增长率']>10]
    return {'regions':rows,'sources':sources,'coverage':len(names),'excluded':sorted(set(left.index)^set(right.index)), 'positive':positive,'negative':negative,'net':positive+negative,'threshold':q,'focus':focus,'start':start,'end':end}

def sensitivity(records: list[dict], end: int) -> list[dict]:
    years={r['year'] for r in records};out=[]
    for window in [3,5,10]:
        if end-window not in years:continue
        result=compare(records,end-window,end)
        for threshold in [5,10,15,20]:
            names=sorted(r['省份'] for r in result['regions'] if r['末年总量']>=result['threshold'] and r['累计增长率'] is not None and r['累计增长率']>threshold)
            out.append({'窗口年数':window,'增长阈值':threshold,'地区数量':len(names),'名单':'、'.join(names) or '无'})
    return out

def quality_experiment(records: list[dict], year: int) -> list[dict]:
    base=[dict(r) for r in records if r['year']==year]
    if not base:return []
    target=max(base,key=lambda r:r['total_mt']);truth=sum(r['total_mt'] for r in base);out=[]
    for scenario in ['原始有效表','重复最大值一行','最大值误乘100万','最大值缺失后填0']:
        rows=[dict(r) for r in base]
        unit='mt'
        if scenario=='重复最大值一行':rows.append(dict(target))
        if scenario=='最大值误乘100万':
            for r in rows:
                if r['province']==target['province']:r['total_mt']*=1e6
        if scenario=='最大值缺失后填0':
            for r in rows:
                if r['province']==target['province']:r['total_mt']=0
        naive=sum(r['total_mt'] for r in rows)
        cleaned,issues,_=clean_records(rows,unit)
        total=sum(r['total_mt'] for r in cleaned)
        out.append({'人工情景':scenario,'直接汇总':naive,'直接偏差百分比':(naive/truth-1)*100 if truth else None,'检查后合计':total,'检查后地区数':len(cleaned),'问题条数':len(issues),'处理后偏差百分比':(total/truth-1)*100 if truth else None})
    return out

def render(records, chart, table):
    import streamlit as st
    import plotly.graph_objects as go
    from charts import style
    years=sorted({r['year'] for r in records})
    if len(years)<2:st.info('增长来源分析至少需要两个年份。');return
    st.subheader('06 增长来自哪里，关注名单是否稳定？')
    l,r=st.columns(2)
    start=l.selectbox('增长分析起年',years[:-1],index=years[:-1].index(years[-1]-5) if years[-1]-5 in years[:-1] else 0)
    end=r.selectbox('增长分析末年',[y for y in years if y>start],index=len([y for y in years if y>start])-1)
    a=compare(records,start,end)
    st.caption(f'只比较两年都有数据的{a["coverage"]}个地区，单位：百万吨。不同覆盖范围的结果不宜直接比较。')
    if not a['regions']:return
    st.write(f'增加地区合计增加 {a["positive"]:,.2f}；减少地区合计减少 {abs(a["negative"]):,.2f}；相抵后净增加 {a["net"]:,.2f}。')
    rr=sorted(a['regions'],key=lambda x:x['增加量'])
    fig=go.Figure(go.Bar(x=[x['增加量'] for x in rr],y=[x['省份'] for x in rr],orientation='h',marker_color=['#a96642' if x['增加量']>=0 else '#d4bda5' for x in rr]))
    fig=style(fig,f'{start}—{end}年各省增加或减少量',800);fig.update_xaxes(title='增加量 / 百万吨');chart(fig,'06_地区增量')
    if all(x['增加量'] is not None for x in a['sources']):
        fig=style(go.Figure(go.Bar(x=[x['来源'] for x in a['sources']],y=[x['增加量'] for x in a['sources']],marker_color='#a96642')),f'{start}—{end}年四类来源增加量');fig.update_yaxes(title='增加量 / 百万吨');chart(fig,'07_来源增量')
    else:st.info('配对地区中分项不完整，暂不计算四类来源合计。')
    table(a['regions'])
    st.markdown('**窗口和阈值敏感性**');table(sensitivity(records,end))
    st.caption('上四分位数按每个窗口的共同地区计算。3、5、10年累计增长不能理解为同一种年增长率；本表用于检验筛选设定的影响，不是显著性检验。')
    st.markdown('**人工数据质量实验**');table(quality_experiment(records,end))
    st.warning('以上错误是从当前有效数据人工构造的对照实验，不代表原清单存在这些错误。规则可能隔离问题但无法恢复真值；地区减少后的合计不等于原完整口径。无分项时，总量单位错误也可能无法自动识别，需回查来源和单位。')
