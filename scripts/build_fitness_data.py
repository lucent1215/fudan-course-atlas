from pathlib import Path
from bs4 import BeautifulSoup
from urllib.request import urlopen
import json,re
HERE=Path(__file__).parent
tables=BeautifulSoup(urlopen('https://fdty.fudan.edu.cn/b0/31/c29222a307249/page.htm',timeout=30).read().decode('utf8'),'html.parser').find_all('table')
data={'standard':'国家学生体质健康标准（2014年修订）· 大学生组','source':'复旦大学体育教学部《国家学生体质健康标准》测试（大学生）评分标准','source_date':'2026-09-16','retrieved':'2026-10-23','weights':{'bmi':15,'lung':15,'sprint':20,'reach':10,'jump':10,'strength':10,'run':20},'groups':{}}
keys=['lung','sprint','reach','jump','strength','run']
for sex,table_index,bonus_index in [('male',2,4),('female',3,5)]:
 for year in [0,1]:
  rows=[]
  for tr in tables[table_index].find_all('tr')[2:]:
   cells=[c.get_text('',strip=True) for c in tr.find_all(['td','th'],recursive=False)]
   if not cells:continue
   if not re.fullmatch(r'\d+',cells[0]):cells=cells[1:]
   if len(cells)!=13:raise ValueError(cells)
   row={'points':int(cells[0])}
   for k,key in enumerate(keys):
    text=cells[1+2*k+year]
    if not text:row[key]=None
    elif key=='run':
     minutes,seconds=text.split('.');row[key]=int(minutes)*60+int(seconds)
    else:row[key]=float(text)
   rows.append(row)
  bonus=[]
  for tr in tables[bonus_index].find_all('tr')[3:]:
   cells=[c.get_text('',strip=True) for c in tr.find_all(['td','th'],recursive=False)]
   if len(cells)!=5:raise ValueError(cells)
   bonus.append({'points':int(cells[0]),'strength_extra':int(cells[1+year]),'run_seconds_faster':abs(int(re.search(r'-?\d+',cells[3+year]).group()))})
  assert len(rows)==20 and len(bonus)==10
  assert rows[0]['points']==100 and rows[-1]['points']==10
  data['groups'][sex+'_'+('12' if year==0 else '34')]={'rows':rows,'bonus':bonus}
assert sum(data['weights'].values())==100
target=HERE.parent/'public/data/fitness.json'
target.write_text(json.dumps(data,ensure_ascii=False,separators=(',',':')),encoding='utf8')
print('FITNESS_DATA_READY',len(data['groups']),'groups')
