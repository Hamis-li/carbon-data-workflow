# 碳数工坊 数据处理演示

以省级碳排放数据展示一条真实流程：**上传 → 查看原始数据 → 清洗检查 → 整理成统一表格 → 服务器计算 → 图表和下载**。

部署入口：`app.py`。代码面向GitHub与Streamlit Community Cloud；也可本地或Docker运行。不需要API密钥，不需要数据库。

## 课堂展示

1. 打开页面，点“一键体验示例”。使用原CEADs工作簿，服务器读取后保留780条省年记录。
2. 查看清洗计数、原表预览和规则。原表无明显脏数据，因此不虚构清洗数量。
3. 查看统一省名、代码、年份、单位后的数据，搜索“北京”或“2022”，下载CSV。
4. 查看折线、柱状、地图、热力图和散点图。更改年份、省份或增长条件，图表随数据重算。
5. 返回首页点“试试带问题的数据”，展示重复、缺失、负数、冲突的实际处理：8条输入，保留2条，单独列出6条原因。
6. 在最后一页下载成果ZIP及完整处理记录。图表工具栏可导出SVG；每图也可下载含全部交互代码的HTML。

## 输入格式

- 原始《中国省级表观碳排放清单（1997—2022）》年度工作簿：从NOTE确认Mt单位，只读各年度第2—6行；不重复加总能源收支明细。
- 统一格式Excel或UTF-8 CSV：第一行至少含`province,year,total_mt`。`coal_mt,oil_mt,gas_mt,cement_mt`可选。
- 若统一表的单位是吨，上传时选择“吨二氧化碳”，服务器换算为百万吨。原CEADs工作簿自动使用NOTE单位。
- 文件上限3MB、输入50,000条、Excel解压后32MB；统一Excel最多100列。不支持任意布局和其他行业表格。

## 清洗规则

省名统一为中文简称，区分Shanxi（山西）与Shaanxi（陕西）；年份须为1900—2100的整数；排放值须为有限非负数字。空值不填0。缺总量而四个分项齐全时用四项之和补齐，并记录数量。分项齐全时核对其和与总量，容差为1e-6百万吨与总量1e-6倍中的较大值。

同省同年且所有排放字段完全相同的记录保留一条；数值有冲突则整组隔离，不擅自挑一条。原工作表、行号、列号保留以便回查。单年缺省会提醒覆盖不一致；缺少上一年或整五年前正值时不强行计算增长率。

## 数据和地图来源

原始排放示例来自[CEADs省级数据目录](https://www.ceads.net.cn/data/carbon-inventory/provincial-level/)，单位为百万吨二氧化碳，1997—2022年30个省级地区。2022年30省合计13402.458335645555百万吨。保留的是表观核算口径，不能直接当作全国官方总量或2026年实时排放。

地图使用课程提供的“中国标准地图-审图号GS(2020)4619号-shp格式”数据包中的省级行政区和国界线。34个省级地区中，西藏、台湾、香港、澳门没有本清单排放值，保留灰色。沿用源文件的兰伯特投影，通过坐标缩放生成网页图形，没有增删边界。审图号是**数据包所标注的底图编号**，不是本次添加统计颜色后的新审图编号。数据包没有给出矢量转换作者及日期，不冒称此次直接从官方站下载。

`data/map.json.gz.b64`是地图显示路径的gzip+Base64表示；`data/sample.xlsx.b64`是原Excel字节的Base64表示，仅为源码传输方便，解码后的内容保持原样。页面在Python服务器中读取并处理用户上传数据，不是只显示预制图；上传文件只保留在当前会话内存，不写长期存储。

## GitHub + Streamlit部署

1. 将本项目文件放在仓库根目录。
2. 登录[Streamlit Community Cloud](https://share.streamlit.io/)，连接GitHub。
3. Create app → 选择仓库`Hamis-li/carbon-data-workflow`、分支`main`、入口`app.py`。
4. Advanced settings中选择Python **3.12**，点击Deploy。应用地址由Streamlit返回，以实际部署成功的URL为准。

参考：[官方部署说明](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy)。GitHub连接与Streamlit账号授权是两步；连接ChatGPT的GitHub不代表已授权Streamlit。

## 本地运行

```bash
python -m pip install -r requirements.txt
streamlit run app.py
```

浏览器打开`http://localhost:8501`。本地启动计算在本机；Community Cloud部署后同一份Python代码运行在云端服务器。

## Docker

```bash
docker compose up --build
```

打开`http://localhost:8501`。提供构建文件，尚未发布镜像仓库。Docker解决环境复用，不会自动变成多机计算。Streamlit Community Cloud直接按requirements运行Python，不使用本Dockerfile。

## 规模更大时

当前程序适合课设和小批量上传，未部署Spark集群。未来可先将原文件放到对象存储，再由任务队列触发按年处理，把结果写进数据库供页面查询。只有单机不够用时，才考虑Spark并行计算。当前的存储、排队和分布式部分仍是扩展方案，不作为已实现能力。

## 测试

```bash
python -m unittest discover -s tests -p 'test_pipeline.py' -v
python tests/test_app.py
```

测试覆盖原始780条清单、错误样例、单位换算、零分母、省名对应、无效输入与跨页操作。
