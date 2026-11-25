# 经管实践调研 CoursePilot

面向上海交通大学学生的个性化选课助手，以安泰金融学专业为演示场景。当前成果包括总体设计、功能说明与本地演示系统。

## 快速入口

- [打开本地系统](http://127.0.0.1:8765/)（需先启动服务）
- [项目现状与后续任务](docs/项目现状与后续任务.md)
- [三阶段痛点与功能说明](经管实践调研/选课系统/CoursePilot-痛点与功能说明.md)
- [总体设计方案](经管实践调研/选课系统/sjtu-ai-course-pilot/sjtu-ai-course-pilot.html)
- [演示与开发说明](经管实践调研/选课系统/coursepilot/README.md)

## 目录说明

```text
经管实践调研/                 当前工作区
├─ README.md                  项目入口
├─ 启动系统.ps1                根目录启动入口
├─ docs/                      项目现状、验证记录与后续任务
└─ 经管实践调研/选课系统/      原有成果与运行路径
   ├─ CoursePilot-痛点与功能说明.md
   ├─ sjtu-ai-course-pilot/    HTML 总体设计及配套资源
   └─ coursepilot/
      ├─ backend/app/         API、求解器、偏好解析与社区接入
      ├─ backend/data/        模拟课程与培养计划
      ├─ frontend/src/        React 界面
      ├─ frontend/dist/       已构建的前端
      ├─ check_ui.py          浏览器交互回归
      └─ start.ps1            原启动脚本
```

## 启动与停止

在本目录运行：

```powershell
powershell -ExecutionPolicy Bypass -File .\启动系统.ps1
```

服务地址为 http://127.0.0.1:8765/，正常前台启动时按 Ctrl+C 停止。
首次配置依赖、前端构建和演示步骤见演示与开发说明。端口已被本系统占用时无需重复启动。

## 数据使用说明

课程难度、负荷、给分和容量主要为演示数据，不能据此作正式选课判断。jCourse 评价需用户配置 API Key 后按需读取，不参与当前推荐评分。教师端、教务看板与学习反馈回写仍是规划或试点设计。
