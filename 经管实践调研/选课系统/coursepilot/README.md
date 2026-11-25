# CoursePilot AI 选课协同工作台

以学生个人建模为基础，将选课咨询、课程推荐、可行课表和修读反馈连接起来。当前为面向上海交通大学安泰金融学场景的本地原型，课程资料使用示例数据。

## 阅读入口

| 读者与用途 | 文档 |
| --- | --- |
| 课堂汇报：个人建模与推荐机制 | [推荐系统与个人建模 Pre 内容稿](docs/推荐系统与个人建模_Pre.md) |
| 课堂汇报：反馈回流与持续改进 | [反馈更新与 RSI 自迭代 Pre 内容稿](docs/反馈更新与RSI自迭代_Pre.md) |
| 后端与数据库开发交接 | [推荐后端与数据库交接](docs/推荐后端与数据库交接.md) |
| 登录、教务导入、LLM 配置 | [登录与教务接入](docs/登录与教务接入.md) |
| 当前迭代算法与接口 | [反馈与 RSI 自迭代](docs/反馈与RSI自迭代.md) |

Pre 文档描述完整目标方案，可作为 PPT 和口头讲稿素材；本 README 描述当前可运行实现。

## 启动

在本目录运行：

```powershell
python -m pip install -r backend/requirements.txt
powershell -ExecutionPolicy Bypass -File .\start.ps1
```

- 学生端：http://127.0.0.1:8765/
- 接口文档：http://127.0.0.1:8765/docs
- 首次进入创建本地账户；请勿使用学校密码。前台运行时 Ctrl+C 停止。
- 修改前端后运行 `npm ci --prefix frontend` 和 `npm run build --prefix frontend`。

## 五分钟演示

1. 注册并登录，查看示例课表、已修记录与培养要求。
2. 打开右下角「选课咨询」，输入「我想学数据分析，周三下午要实习」。
3. 点击「按这个安排更新课表」，查看禁排、兴趣匹配与候选方案。
4. 锁定一门课程，把另一教学班标记满员；比较备选，确认采用，导出清单。
5. 在咨询窗口选择「反馈选课与修读情况」，填写修读状态和投入，也可撤回。
6. 用后端迭代测试说明候选策略如何通过验证、被拒绝或回退。普通账户不会在少量反馈下立即触发策略升级。

## 当前实现

| 模块 | 已实现 |
| --- | --- |
| 学生工作台 | 课表对比、禁排、锁定、满员备选、撤销、离线清单 |
| 身份与持久化 | 本地注册登录、Cookie 会话、学生档案访问隔离；账户 SQLite，档案 JSON |
| 对话与画像 | 后端规则解析、待确认画像、对话记录、反馈保存 |
| 推荐算法 | 五维评分、个体兴趣修正、束搜索及时间/先修/学分约束 |
| 反馈与更新 | 明确反馈学习、结果分类、实际负荷记录、修改与撤回 |
| 个人负荷校准 | 同学期至少三门已完成课程，自报投入校准个人估计，幅度不超过 ±20% |
| 有界自迭代 | 候选参数、训练/验证/测试划分、采用门槛、新测试课程检查、版本审计、基线回退 |
| 对接准备 | StudentRepository、学校身份与教务数据接口、JSON 导入、后端 LLM 配置口 |

LLM 当前使用规则占位，不调用外部服务；个人微调、学校 SSO、官方实时选课数据、教师审核与教务扩容流程尚未接通。有限宽度搜索未找到方案不等于数学无解；模拟验证不代表真实选课效果提升。

## 代码结构

```text
backend/app/
  main.py          服务入口与依赖装配
  auth.py          本地身份与学校认证接口
  academic.py      教务数据模型与导入适配
  repository.py    学生存储协议与文件实现
  personal.py      对话、画像、反馈、个性化推荐接口
  llm_gateway.py   LLM 地址、模型名、Token 占位
  solver.py        课程评分与课表求解
  iteration.py     修读反馈、候选评估、版本回退
  calibration.py   个人负荷校准
frontend/src/
  App.tsx          课表工作台
  components/LoginGate.tsx       登录界面
  components/CourseAssistant.tsx 悬浮咨询与反馈入口
```

档案默认保存在 `backend/data/students/`，账户保存在 `backend/data/auth.sqlite3`。真实数据与凭据不应提交到仓库。学校导入使用 `backend/import_academic.py`，配置方法见交接文档。jCourse 可选只读评价接入沿用 `JCOURSE_API_KEY`，不改变正式选课记录。

## 验证

在项目目录运行：

```powershell
python backend/check_personal_api.py
python backend/check_identity.py
python backend/check_iteration.py
python backend/check_calibration.py
python backend/check_demo.py
python backend/check_learning.py
python check_login.py
```

浏览器测试需要 Playwright 与 Microsoft Edge，API 测试需要 httpx。`check_login.py` 创建随机本地测试账户。历史 `check_assistant.py`、`check_personal.py` 对应已移除的调试面板；其他旧浏览器测试需补登录前置，不是当前完整验收入口。
