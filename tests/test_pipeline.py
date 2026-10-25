import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from pipeline import process_file,clean_records,analyse,province_name
ROOT=Path(__file__).resolve().parents[1]
class PipelineTests(unittest.TestCase):
 def test_original_workbook(self):
  from app_assets import sample_bytes
  r=process_file(sample_bytes(),'sample.xlsx')
  self.assertEqual(r['summary'],{'input':780,'kept':780,'excluded':0})
  self.assertAlmostEqual(r['analysis']['annual'][-1]['total_mt'],13402.458335645555,places=7)
  self.assertEqual(len(r['analysis']['years']),26)
  self.assertEqual(len([a for a in r['analysis']['features'] if a['focus']]),5)
  self.assertEqual(len(r['analysis']['missing_regions']),4)
 def test_dirty_records(self):
  r=process_file((ROOT/'data/issues-example.csv').read_bytes(),'issues.csv')
  self.assertEqual(r['summary'],{'input':8,'kept':2,'excluded':6})
  self.assertEqual(r['changes']['derived'],1);self.assertEqual(r['changes']['exact_duplicates'],1);self.assertEqual(r['changes']['conflicts'],2)
  self.assertIsNone(r['analysis']['base'])
 def test_unit_zero_and_alias(self):
  records,_,_=clean_records([{'province':'北京市','year':2017,'total_mt':0},{'province':'Beijing','year':2022,'total_mt':1000000}],'tonnes')
  self.assertEqual(records[-1]['total_mt'],1);self.assertIsNone(analyse(records)['features'][0]['growth_pct'])
  self.assertEqual(province_name('Shaanxi'),'陕西');self.assertEqual(province_name('Shanxi'),'山西')
 def test_invalid_and_inconsistent(self):
  records,issues,_=clean_records([{'province':'北京','year':2022,'total_mt':10,'coal_mt':1,'oil_mt':1,'gas_mt':1,'cement_mt':1},{'province':'北京','year':2022.5,'total_mt':2},{'province':'北京','year':2022,'total_mt':'inf'}])
  self.assertEqual(len(records),0);self.assertEqual(len(issues),3)
 def test_partial_coverage(self):
  records,_,_=clean_records([{'province':'北京','year':2021,'total_mt':1},{'province':'北京','year':2022,'total_mt':2},{'province':'天津','year':2022,'total_mt':2}]);self.assertFalse(analyse(records)['annual'][0]['complete'])
 def test_bad_input(self):
  with self.assertRaises(ValueError):process_file(b'wrong,header\n1,2','bad.csv')
  with self.assertRaises(ValueError):process_file(b'a'*4000000,'huge.csv')
if __name__=='__main__':unittest.main()
