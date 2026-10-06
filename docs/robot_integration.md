# 工业机器人集成学习与后续实机接口

本版本机器人是 Cartesian TCP 仿真，HOME→PrePick→Pick→Lift→PrePlace→Place→Home。没有使用 KUKA 控制器或六轴模型。与 KUKA 类项目相贴的是 Base/Tool/TCP 的概念、任务握手、目标合法性检查和停止恢复。

概念任务可描述为：

```text
PTP HOME
PTP PRE_PICK
LIN PICK
GRIPPER_CLOSE / WAIT CLOSED_FEEDBACK
LIN PRE_PICK
PTP PRE_PLACE
LIN PLACE
GRIPPER_OPEN / WAIT OPEN_FEEDBACK
LIN PRE_PLACE
PTP HOME
```

这是动作意图说明，不是可以下载的 KRL 程序。PTP 由关节空间决定，路径并非直线；LIN 要求笛卡尔连续轨迹及可达性。当前仿真仅按线段积分，不能据此声称完成工业机器人 PTP/LIN 调试。

真实集成的最小验证顺序：

1. 确認具体机器人/控制器型号及厂家通信选件，读取原厂模型与安全配置。
2. 建立 Base 和 Tool 标定，校对相机坐标、TCP 偏置与工件高度。
3. ROS2/MoveIt 阶段导入经确认的 URDF、关节限位和 collision mesh，用 Planning Scene 包含夹具、输送线和料盘。
4. 给预抓/抓取/放置位姿解 IK，碰撞与关节速度/加速度检查通过后生成轨迹；不要把此版本 TCP 检查当作连杆碰撞检查。
5. 配置仿真反馈与超时，确认每个任务事务号匹配、Complete 卡高拒绝下一任务。
6. 厂家认可的仿真控制器验证后，按现场流程进行低速点动、空跑、带工件验证与重复定位测量。

该后续阶段未实现，README 和简历不把 ROS2/MoveIt/KUKA 真机列为已完成技术。
