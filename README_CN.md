# 中文运行与项目说明

RoboFlex Cell 的主线是“非标自动化工作站闭环”：设备流程负责组织机器人、视觉、夹爪、输送线、传感器反馈和异常恢复。可以在没有机器人硬件的电脑上演示与测试。仓库首页和 `docs/requirements.md` 明确哪些是已运行软件，哪些是未验证概念设计。

## 安装

1. 安装 Python 3.10–3.12 和 Git，确认 `python --version` 有正常输出。
2. 克隆仓库进入目录，运行 `python -m venv .venv`。
3. PowerShell 运行 `.\.venv\Scripts\python.exe -m pip install -e ".[test]"`。
4. 运行 `.\.venv\Scripts\python.exe -m roboflex.cli serve`，打开 http://127.0.0.1:8080 。

不要求执行环境激活脚本，避免 PowerShell 执行策略影响。可通过 `--port 8090` 更换本地端口；退出终端服务使用 Ctrl+C。Linux/macOS 用 `.venv/bin/python`。

## 演示顺序

先“启动 AUTO”：模拟来料 → 停带 → 合成相机图像 → 图像识别与位置输出 → 抓取 → 分类料盘 → 合成质检 → 回家 → 完成统计。SVG 连线是 TCP 示意，不是六轴数字孪生。真实仿真状态在服务端推进，网页只显示。

选 `robot_timeout` 注入，运动冻结后约 6 s 仿真时间出现 ALM-004。输送线停止，RobotRunning 撤销，第一条报警与出错工序保持。直接 Start 被拒绝。点击“解除故障”，如已持件勾选人工清理，再“人工复位”。系统回 IDLE，重新 Start 后可再完成正常循环。

可演示门禁：机器人已持件时注入 `door_open`，下一扫描停止、保留夹爪命令和当前位置。解除门禁后先尝试不勾选清理复位，观察联锁拒绝，再勾选清理复位。这里的清理是模拟操作员确认，不是真机远程开爪。

“停止”是要求清理与复位的停止。本版本没有暂停续跑。故障选项是一次一个；注入下一种前先解除/复位。NG 为合成放置失败，当前没有 NG 料盘搬运流程。

## 数据与图纸

`benchmark` 默认写入被 Git 忽略的 `artifacts/benchmark/`，不会覆盖仓库保留的证据。`docs/evidence/benchmark/` 是交付时实跑的100次记录，定位误差相对于独立保存的工件真值。随机种子和扫描周期固定，循环记录可重现；墙钟用时随电脑改变。

`calibration_report.py` 生成20组带0.6 px噪声的标定，每组用50个未参与标定的点验证，避免只看标定拟合残差。它使用非仿射投影作为独立几何真值，不是实物标定板实验。

图纸可直接在 GitHub 查看 SVG；DXF 可用支持 R12 的 CAD 工具打开。尺寸、BOM 和电气地址均为概念设计，施工/制造前需要厂家数据、机械校核和设备安全设计。未提供 SolidWorks 原生文件，也未运行 CODESYS。

## 常见问题

- `python` 没有版本输出：可能是 Windows 应用执行别名；安装实际 Python，或使用已有解释器的绝对路径。
- 无 `roboflex` 命令：使用 `.\.venv\Scripts\python.exe -m roboflex.cli ...`，并确认在项目目录执行了 pip 安装。
- 地址占用：添加 `serve --port 8090`，浏览器打开相同端口。
- Start 拒绝：查看报警、解除注入原因、完成清理并人工复位；系统必须在 IDLE。
- 图像为空：启动前没有工件，黑色画面属于正常等待状态。
- 浏览器仿真时间比现实慢：逻辑扫描每次固定10ms，服务不是实时控制器。节拍报告不能当实体设备节拍。

面试讲解顺序、可以据实放进简历的文字见 [`docs/interview_and_resume.md`](docs/interview_and_resume.md)。
