# Pure Pursuit - 启动说明

## 环境要求

- ROS 2 Humble
- Python 3.10+
- NumPy (`python3-numpy`)
- colcon
- Gazebo Fortress (Ignition Gazebo)
- ros_gz_bridge / ros_gz_sim

## 构建

```bash
cd /home/cyr/pp/pure_pursuit
colcon build --packages-select pure_pursuit
```

## 运行

先 source 环境：

```bash
source /opt/ros/humble/setup.bash
source install/setup.bash
```

### 方式一：Launch 文件（推荐，同时启动路径发布 + 控制器）

```bash
ros2 launch pure_pursuit pure_pursuit.launch.py
```

### 方式二：ros2 run 分别启动

```bash
# 终端1：发布 CSV 中的参考路径（latched，发布后保持存活）
ros2 run pure_pursuit csv_path_publisher

# 终端2：运行纯追踪控制器（持续运行）
ros2 run pure_pursuit pure_pursuit_node
```

### 方式三：直接 Python 运行（开发调试用）

```bash
python3 pure_pursuit/csv_path_publisher.py
python3 pure_pursuit/node.py
```

---

## Gazebo 仿真（完整闭环）

### 1. 安装 Gazebo Fortress

```bash
sudo apt install -y ignition-fortress ros-humble-ros-gz-sim ros-humble-ros-gz-bridge ros-humble-ackermann-msgs
```

### 2. 编译

```bash
cd /home/cyr/pp/pure_pursuit
colcon build --packages-select pure_pursuit
```

### 3. 启动仿真

```bash
source /opt/ros/humble/setup.bash
source install/setup.bash

# 设置模型搜索路径
export IGN_GAZEBO_RESOURCE_PATH=/home/cyr/pp/pure_pursuit/models:$IGN_GAZEBO_RESOURCE_PATH

# 一键启动
ros2 launch pure_pursuit sim_pp_bringup.launch.py
```

启动后依次发生:
1. Gazebo Fortress 打开, 显示地面平面
2. 3 秒后蓝色小车 spawn 在地面上
3. ros_gz_bridge 建立 odom/ackermann/clock 三通道桥接
4. csv_path_publisher 发布参考路径
5. pure_pursuit_node 开始路径跟踪规划
6. vehicle_ackermann_controller 将 (v,δ) 转为 AckermannDriveStamped 驱动小车

### 4. 调试话题

```bash
source install/setup.bash

# 查看规划输出
ros2 topic echo /target_speed_vdelta

# 查看底盘控制指令
ros2 topic echo /ackermann_cmd

# 查看车辆里程计
ros2 topic echo /chcn_vehicle_state

# 查看预瞄点可视化
ros2 topic echo /target_point
```

### 5. AckermannDrive 桥接说明

桥接配置文件: `config/gz_bridge.yaml`

如果启动时报 "failed to create bridge for /ackermann_cmd"，说明你的 `ros_gz_bridge` 版本未内置 `ackermann_msgs` ↔ `ignition.msgs.AckermannDrive` 映射。两种解决方式:

**(a) 检查支持的类型对:**
```bash
ros2 run ros_gz_bridge parameter_bridge --print-all 2>&1 | grep -i ackermann
```

**(b) 如不支持, 升级 ros_gz_bridge 或使用 ros-humble-ros-gz-sim-dbgsym 包:**
```bash
sudo apt install -y ros-humble-ros-gz-sim-dbgsym
```

**(c) 最后兜底: 用 ign 命令行直接发指令测试:**
```bash
ign topic -t /model/vehicle/ackermann -m ignition.msgs.AckermannDrive -p "speed: 1.0, steering_angle: 0.2"
```

## 指定自定义 CSV 路径

通过参数覆盖默认的 `data/path.csv`：

```bash
ros2 run pure_pursuit csv_path_publisher --ros-args -p csv_path:=/path/to/your/path.csv
```

Launch 方式：

```bash
ros2 launch pure_pursuit pure_pursuit.launch.py csv_path:=/path/to/your/path.csv
```

## 验证测试

使用虚拟里程计配合原有 launch 进行集成验证，无需修改代码。

**终端 1：启动虚拟里程计**

```bash
source install/setup.bash
python3 test/test_odom_publisher.py
```

> 循环发布 `test/test_odom.csv` 中的姿态到 `/chcn_vehicle_state`，模拟车辆运动。

**终端 2：启动原版 pure_pursuit**

```bash
source install/setup.bash
ros2 launch pure_pursuit pure_pursuit.launch.py
```

验证控制器输出话题：

```bash
source install/setup.bash
ros2 topic echo /target_speed_vdelta
```

## 参数配置

控制器参数位于 `config/pp_params.yaml`：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `wheelbase` | 1.5 | 轴距 [m] |
| `v_base` | 5.0 | 直线基准速度 [m/s] |
| `R0` | 2.0 | 半速曲率半径 [m] |
| `Ld_min` | 1.0 | 最小预瞄距离 [m] |
| `Ld_max` | 5.0 | 最大预瞄距离 [m] |
| `accel` | 1.0 | 最大加速度 [m/s²] |
| `decel` | 2.0 | 最大减速度 [m/s²] |
| `cur_windows` | 8.0 | 圆弧拟合窗口弧长 [m] |
| `odom_timeout` | 20 | 里程计超时计数 |
| `hz` | 20 | 控制频率 [Hz] |

## 话题接口

| 话题 | 类型 | 方向 | 说明 |
|------|------|------|------|
| `/chcn_vehicle_state` | `nav_msgs/Odometry` | 订阅 | 车辆位姿与速度 (BestEffort) |
| `/global/reference_path` | `nav_msgs/Path` | 订阅 | 参考路径 (TransientLocal, latched) |
| `/target_speed_vdelta` | `std_msgs/Float64MultiArray` | 发布 | `[目标速度, 前轮转角]` |
| `/target_speed` | `std_msgs/Float64` | 发布 | 目标速度 |
| `/target_point` | `visualization_msgs/Marker` | 发布 | 预瞄点可视化 (红色球体) |
