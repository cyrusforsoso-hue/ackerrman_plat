# Ackermann 小车 Gazebo 仿真平台

基于 ROS2 Humble + Gazebo 的阿克曼转向小车仿真项目，集成 Pure Pursuit 规划算法，并提供 Web 前端算法测试平台，支持第三方规划算法接入测试。

---

## 1. 环境要求

| 依赖 | 版本 |
|------|------|
| 操作系统 | Ubuntu 22.04 |
| ROS2 | Humble |
| Python | 3.10+ |
| Gazebo | 与 ROS2 Humble 配套版本 |
| Node.js | 18+ (前端界面需要) |

---

## 2. 安装依赖

### 2.1 ROS2 功能包

```bash
sudo apt install ros-humble-ros2-control ros-humble-ros2-controllers
sudo apt install ros-humble-ackermann-msgs
sudo apt install ros-humble-nav-msgs
sudo apt install ros-humble-joint-state-publisher-gui
sudo apt install ros-humble-gazebo-ros2-control
sudo apt install ros-humble-xacro
```

### 2.2 Python 后端依赖

```bash
cd ~/ackermann_gazebo
pip install -r src/ackermann_platform/backend/requirements.txt
```

### 2.3 Node.js 前端依赖

```bash
cd ~/ackermann_gazebo/src/ackermann_platform/frontend
npm install
```

---

## 3. 编译

```bash
cd ~/ackermann_gazebo
colcon build --symlink-install
source install/setup.bash
```

---

## 4. 使用教程

### 4.1 启动仿真 + Pure Pursuit 规划

```bash
# 终端1: 启动 Gazebo 仿真
source install/setup.bash
ros2 launch racebot_control racebot.launch.py

# 终端2: 启动 Pure Pursuit 规划器
source install/setup.bash
ros2 launch pure_pursuit pure_pursuit_planner.launch.py

# 终端3: 键盘控制 (可选, 用于手动接管)
source install/setup.bash
ros2 run racebot_control keyboard_teleop.py
```

### 4.2 启动算法测试平台 (Web 界面)

一键启动所有组件（Gazebo + 后端 + 前端）：

```bash
source install/setup.bash
./src/ackermann_platform/start_platform.sh
```

浏览器打开 **http://localhost:5173** 进入测试平台。

**平台功能：**
- **Mode A** — 输入外部 ROS topic（如 `/my_planner/ackermann_cmd`），平台自动桥接到小车控制
- **Mode B** — 上传或粘贴 Python 规划脚本（继承 `PlannerBase` 接口），平台动态加载运行
- **实时监控** — 车速、位置、横向偏差、连接状态
- **2D 轨迹可视化** — 参考路径 + 实际行驶轨迹叠加显示
- **路径管理** — 上传/激活/删除 CSV 路径文件

如果 Gazebo 已运行，可以跳过仿真启动：

```bash
./src/ackermann_platform/start_platform.sh --no-gazebo
```

后台服务端口：
- 前端: http://localhost:5173
- 后端 API: http://localhost:8000
- API 文档: http://localhost:8000/docs

---

## 5. 项目结构

```
ackermann_gazebo/
├── src/
│   ├── racebot_description/    # 车辆 URDF/Xacro 模型 + 网格文件
│   ├── racebot_control/        # 控制器: 伺服、里程计、坐标变换、键盘遥控
│   ├── pure_pursuit/           # Pure Pursuit 规划算法 + CSV 路径发布
│   └── ackermann_platform/     # 算法测试平台 (Web 前后端)
│       ├── backend/            # FastAPI 后端 + ROS2 桥接
│       ├── frontend/           # React 前端界面
│       ├── start_platform.sh   # 一键启动脚本
│       └── example_user_planner.py  # 用户算法示例
├── docs/
│   ├── superpowers/specs/      # 设计文档
│   ├── superpowers/plans/      # 实现计划
│   └── ai-development-experience.md  # AI 开发经验总结
└── README.md
```

### ROS2 Topic 说明

| Topic | 类型 | 方向 | 说明 |
|-------|------|------|------|
| `/odom` | `nav_msgs/Odometry` | 发布 | 车辆里程计 (位置+速度) |
| `/ackermann_cmd` | `ackermann_msgs/AckermannDriveStamped` | 订阅 | 车辆控制指令 (速度+转角) |
| `/global/reference_path` | `nav_msgs/Path` | 发布 | 参考路径 (CSV 路径点) |
| `/target_speed_vdelta` | `std_msgs/Float64MultiArray` | 发布 | Pure Pursuit 输出 [v, δ] |

---
