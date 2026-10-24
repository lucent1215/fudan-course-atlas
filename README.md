# 复旦选课地图

[在线使用](https://fudan-course-atlas.xiasinm.chatgpt.site) · [参与修改](CONTRIBUTING.md) · [提交反馈](https://github.com/pythonbug225/fudan-course-atlas/issues)

按课程代码、课程名、教师名和拼音首字母检索复旦课程，课程卡片按AI、数学、其他专业课与GE代码分类着色，逐班比较学习收益、时间负担与成绩风险。每门课保留四部分：课程大纲、课程资料、树洞评论、对比和总结。

## 功能

- 课程检索：公共方案＋一个专业方案，支持学期、班型、课程要求、代码前缀和通识模块筛选。
- 调查图按课程与教师拆分到详情，保留推测、小班、未注明教师等原始标记。
- 教务与数院两种GPA口径：数院另分2027届推免累计70分和2024级奖学金学年修正，A+4.3、总/专业各50%，推免并列现行与旧固定版。
- 体育必修按用户提供的固定分档映射；其他课程仍按本课分档与实际浮动绩点处理。
- 单门及多门课GPA试算，可从教学班清单加入课程；P/NP与浮动绩点区间单独处理。
- 等级与绩点表；按用户填写的本课分档计算原始分数、等第、绩点，同分按不同分数值确定映射位次。
- 选课规则：24项官方规则与办理提醒，记录版本、适用范围与条款；过期学期窗口明确标记。
- 上传课评/资料：可分别发布到评论区和资料区，按课程、教师、学期与班型发布，支持附件在线预览和删除自己的投稿。
- 国家体测计算器：大学男生/女生、大一大二/大三大四、七项标准分及两项附加分。

公开数据集包含1006组课程、3543个教学班、3289份保存的大纲与663条综合判断，主要对应2026春秋开课资料。缺少的评价与大纲明确保留缺项。课程详情只显示来源说明，不提供原文跳转链接。

## 所有人怎样参与编辑

仓库为公开仓库。登录GitHub后，任何人都可以Fork、在自己的副本中修改，再向这里提交Pull Request；也可以直接在网页中点击文件的编辑按钮，按GitHub提示创建Fork和PR。直接写入主分支需要维护者授予协作者权限，公开仓库不等于所有访问者都能直接推送。

修改方法见 [CONTRIBUTING.md](CONTRIBUTING.md)。讨论与课程资料补充可以使用Issues或Discussions。PR合并与生产网站发布是两个步骤，合并不会自动修改在线网站。

## 本地运行

网站使用Vinext / Cloudflare Worker，保留原静态课程界面，并新增D1课评存储与R2附件。Node.js要求≥22.13。

```shell
npm ci
npm run build
```

本地预览首次运行需依次执行 `drizzle/` 内SQL（仅本地，按生成顺序，已经执行的不要重复）：

```shell
node --import ./scripts/sites-env.mjs ./node_modules/wrangler/bin/wrangler.js d1 execute DB --local --config dist/server/wrangler.json --persist-to .wrangler/state --file drizzle/0000_mysterious_misty_knight.sql
npm run dev
```

本地开发登录由模板模拟；生产登录由Sites提供。公开浏览无需登录，发布和删除自己的投稿需登录。课评公开显示昵称，服务端身份不返回浏览器。附件支持PDF、PNG、JPG、TXT、Markdown，最多3个、每个8MB。写入接口校验同源、登录、字段和文件格式，24小时内每个账号最多投稿10篇。使用自己的部署环境时，配置逻辑绑定 `DB` 与 `BUCKET`；数据不会随源码或构建产物导出。

## 运行测试与更新索引

计算组件测试可在安装Node.js后执行：

```shell
npm test
```

测试涵盖学分加权、P/NP排除、等第内同分映射、男女及年级分组、国标档位、时间格式与附加分。

课程名、教师名或开课代码变更后，重新生成检索索引：

```shell
python -m pip install -r requirements.txt
python scripts/build_search.py
```

`python scripts/build_fitness_data.py` 可从复旦体育教学部公开页面重新解析体测表；更新后请检查标准适用范围并运行测试。

## 目录

| 路径 | 内容 |
| --- | --- |
| `public/index.html` | 页面和组件结构 |
| `public/assets/app.js` | 检索、筛选、课程详情和逐班比较 |
| `public/assets/components.js` | GPA、分数映射和体测计算 |
| `public/data/catalog.json` | 课程、教学班、逐师综评和匿名摘录 |
| `public/data/search.json` | 课程代码、名称与教师拼音首字母索引 |
| `public/data/survey.json` | 调查图结构化记录及课程对应关系 |
| `public/data/grading.json` | 成绩制度依据与适用范围 |
| `public/data/fitness.json` | 国家体测大学生组评分档位 |
| `public/syllabi/` | 按教学班保存的大纲内容 |
| `public/data/rules.json` | 已核验的官方选课规则及条款出处 |
| `app/api/`、`lib/community.ts` | 课评与附件接口，登录和权限检查 |
| `db/`、`drizzle/` | 数据结构与不可变迁移记录 |
| `tests/`、`scripts/` | 可独立运行的计算测试与数据生成脚本 |

## 材料与适用范围

课程体验按教师、班型、学期分别理解。调查图是调查材料，未提供样本量和时间范围，不代表实际班级分布，也不用于估计拿A概率。2024版数学学院手册与2026级荣誉项目按对应年级区分；完整方案由公共部分与本人专业部分共同组成。

成绩制度、国家体测和原始资料保留各自来源。第三方PDF、匿名摘录与调查图沿用原有权利和许可；数学资料汇编保留原文件署名与许可页。本仓库的公开协作不改变第三方材料原有许可。

端到端投稿验证：安装或指定Playwright模块后运行 `node tests/community.e2e.cjs`（仅面向本地开发登录，不在生产创建测试课评）。
