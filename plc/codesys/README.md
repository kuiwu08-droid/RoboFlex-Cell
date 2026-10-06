# CODESYS Structured Text 参考程序

这些 `.st` 文件是 **POU 源代码参考**，不是已编译的 `.project`、PLCopen XML 或下载到控制器的工程。Python 测试验证 Python 仿真，不能证明 ST 程序已运行。本机未使用 CODESYS 编译器，所以 ST 编译、任务调度、物理 I/O 和联机测试均待完成。

在 CODESYS 3.5 中创建 Standard Library 的 `TON`、`R_TRIG` 功能块可用的工程，逐个创建对应 FB。文件中的 FUNCTION_BLOCK/VAR 部分放到声明区，执行逻辑放到实现区；末尾 END_FUNCTION_BLOCK 属于文本组织，不应粘贴进实现区。创建 10 ms 周期任务并实例化这些块。

建议调用顺序：设备 FB（输入上一扫描的 Sequence 输出，更新反馈）→ Sequence → Conveyor/Alarm 输出映射。确保所有 FB 每扫描调用一次；安全输出应当在所有逻辑之后再次统一屏蔽。`FB_Robot` 的 Execute 必须在每个任务之间变为 FALSE 至少一扫描；GRIP/RELEASE/CHECK 状态用于释放上一任务。只有 RobotDone 才能进入下一工序。

| FB | 职责 |
|---|---|
| FB_Sequence | 流程、启动沿、复位沿、计数、联锁 |
| FB_Robot | Start/Running/Complete/Ack 握手，启动/执行/确认超时 |
| FB_Vision | Trigger/ResultValid/Ack 握手，连接与超时检测 |
| FB_Conveyor | 输送线输出门控 |
| FB_Gripper | 夹爪开闭反馈、超时、停止时保留夹持命令 |
| FB_Alarm | 锁存第一条故障，人工有效复位后清除 |

Sequence 的 `JobNumber` 对应 pick/place/home。该信号本身不携带目标位姿；位姿有效性、目标编号、通信 CRC/事务号和机器人驱动适配需要在真实工程的网关中补充，不能把这个参考程序直接接到真机。

Python 中合成反馈用于快速故障演示，ST 中需要真实布尔反馈；两者按相同的流程意图设计，并未做逐扫描等价证明。ST 的质量检测超时为 2 s，Python 的合成质量检测为 0.1 s；这是不同测试环境的参数，不是物理节拍验证。

建议完成：① 仿真 I/O 映射；② 每阶段正常/超时测试；③ 复位与启动长按测试；④ RobotComplete 卡高测试；⑤ 掉线后禁止自动恢复；⑥ 在 CODESYS 仿真环境记录扫描与 TON 结果。

参考：[TON 官方文档](https://content.helpme-codesys.com/en/libs/Standard/3.5.17.0/Timer/TON.html)、[R_TRIG 官方文档](https://content.helpme-codesys.com/en/libs/Standard/Current/Trigger/R_TRIG.html)。普通 PLC 逻辑只观察安全状态，实体设备的安全功能需要独立的安全硬件设计。
