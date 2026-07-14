# Ackermann Gazebo

## 项目结构

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
└── README.md
```

## 环境依赖

安装依赖功能包:

```
sudo apt install ros-melodic-joint-state-publisher-gui
sudo apt install ros-melodic-ros-control
sudo apt install ros-melodic-ros-controllers
sudo apt install ros-melodic-gmapping
sudo apt install ros-melodic-ackermann-msgs
sudo apt install ros-melodic-navigation
sudo apt install ros-melodic-teb-local-planner
```

