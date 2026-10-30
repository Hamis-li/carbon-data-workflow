"""Run: python reproduce.py. Outputs contain no manually entered findings."""
from pathlib import Path
import json
from app_assets import sample_bytes
from pipeline import process_file, safe_csv, json_safe
from research import compare, sensitivity, quality_experiment

def main():
    out=Path('outputs');out.mkdir(exist_ok=True)
    result=process_file(sample_bytes(),'sample.xlsx')
    records=result['records'];a=compare(records,2017,2022)
    assert len(records)==780
    assert abs(sum(r['增加量'] for r in a['regions'])-a['net'])<1e-7
    assert abs(sum(r['增加量'] for r in a['sources'])-a['net'])<1e-7
    assert quality_experiment(records,2022)[1]['处理后偏差百分比']==0
    tables={'统一数据':records,'地区增量':a['regions'],'来源增量':a['sources'],'敏感性':sensitivity(records,2022),'人工质量实验':quality_experiment(records,2022)}
    for name,rows in tables.items():(out/(name+'.csv')).write_bytes(safe_csv(rows))
    (out/'结果.json').write_text(json.dumps(json_safe({'file':result['file'],'comparison':a}),ensure_ascii=False,indent=2),encoding='utf-8')
    print('PASS: 780 records; regional and source totals agree; duplicate removed. Outputs: outputs/')

if __name__=='__main__':main()

