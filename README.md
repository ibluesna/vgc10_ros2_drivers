# vgc10_ros2_drivers

ROS2 driver for the OnRobot VGC10 vacuum gripper. Controls the gripper via Modbus TCP through an OnRobot Compute Box.

## System Architecture

```
[Your ROS2 Node]
      ↓ publish /OnRobotVGOutput  (grip/release command)
OnRobotVGTcpNode  ←→  Compute Box (192.168.1.1:502, Modbus TCP)  ←→  VGC10 Gripper
      ↓ publish /OnRobotVGInput   (vacuum status)
[Your ROS2 Node]
```

## Hardware Setup

- Connect the Compute Box to your PC via Ethernet (Cat 5e, max 3m)
- Connect the VGC10 to the Compute Box via the tool data cable (blue cable → DEVICES port)
- Compute Box default IP: **192.168.1.1** (DIP switch 3 ON)
- Your PC is auto-assigned an IP in range **192.168.1.100–105**

Verify connectivity before launching:
```bash
ping 192.168.1.1
```

## Package Structure

| Package | Description |
|---------|-------------|
| `vgc10_control` | Main ROS2 nodes for control and status monitoring |
| `vgc10_modbus_tcp` | Modbus TCP communication library |
| `vgc10_msgs` | Custom ROS2 message definitions |
| `vgc10_description` | URDF/xacro robot description files |

## Dependencies

```bash
sudo apt install ros-jazzy-rclpy
pip install pymodbus
```

## Build

```bash
cd ~/sensor_ws
colcon build --packages-select vgc10_msgs vgc10_modbus_tcp vgc10_control
source install/setup.bash
```

Add to `~/.bashrc` to auto-source:
```bash
echo "source ~/sensor_ws/install/setup.bash" >> ~/.bashrc
```

## Launch

```bash
ros2 launch vgc10_control bringup.launch.py
```

Parameters in [bringup.launch.py](vgc10_control/launch/bringup.launch.py):

| Parameter | Default | Description |
|-----------|---------|-------------|
| `/onrobot/ip` | `192.168.1.1` | Compute Box IP address |
| `/onrobot/port` | `502` | Modbus TCP port |
| `dummy` | `false` | Set `true` to run without hardware |

## ROS2 Topics

### Command (publish to grip/release)

**Topic:** `/OnRobotVGOutput`  
**Type:** `vgc10_msgs/msg/OnRobotVGOutput`

| Field | Type | Description |
|-------|------|-------------|
| `rmca` | uint16 | Channel A mode: `0`=Release, `256`=Grip, `512`=Idle |
| `rvca` | uint16 | Channel A vacuum target (0–80%) |
| `rmcb` | uint16 | Channel B mode: `0`=Release, `256`=Grip, `512`=Idle |
| `rvcb` | uint16 | Channel B vacuum target (0–80%) |

### Status (subscribe to detect grasp)

**Topic:** `/OnRobotVGInput`  
**Type:** `vgc10_msgs/msg/OnRobotVGInput`

| Field | Type | Description |
|-------|------|-------------|
| `gvca` | uint16 | Channel A actual vacuum (0–1000, where 1000 = 100%) |
| `gvcb` | uint16 | Channel B actual vacuum (0–1000, where 1000 = 100%) |

## Usage Examples

### Grip (Channel A, 40% vacuum)
```bash
ros2 topic pub --once /OnRobotVGOutput vgc10_msgs/msg/OnRobotVGOutput \
  "{rmca: 256, rvca: 40, rmcb: 0, rvcb: 0}"
```

### Release
```bash
ros2 topic pub --once /OnRobotVGOutput vgc10_msgs/msg/OnRobotVGOutput \
  "{rmca: 0, rvca: 0, rmcb: 0, rvcb: 0}"
```

### Monitor vacuum status
```bash
ros2 topic echo /OnRobotVGInput
```

## Grasp Detection

The pump overshoots slightly above the target before stabilizing.  
Typical behavior when gripping at `rvca=40` (40% target):

```
gvca:   0 →  78 → 595 (peak) → ~540 (stable)   ← object grasped
gvca:   0 →   5 →  10 →   8  →    3 (stable)   ← no object
```

**Recommended threshold: `gvca > 500`** to confirm a successful grasp.

```python
def gripper_status_callback(self, msg):
    GRASP_THRESHOLD = 500
    grasped = msg.gvca > GRASP_THRESHOLD or msg.gvcb > GRASP_THRESHOLD
    if grasped:
        self.get_logger().info("Object grasped!")
```

## Channels A and B

The VGC10 has two independent vacuum channels. Which suction cups belong to which channel is marked on the gripper housing.

```
┌──────────────────────────┐
│  [Cup A][Cup A] | [Cup B][Cup B]  │
│     Channel A      Channel B      │
└──────────────────────────┘
```

Use both channels for heavy objects, or independently for different grip zones.

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `The passed message type is invalid` | Workspace not sourced | `source ~/sensor_ws/install/setup.bash` |
| Topics work but gripper doesn't move | `.value` missing on ROS2 parameters (fixed) | Rebuild after fix |
| `Executor is already spinning` | Thread created inside loop (fixed) | Rebuild after fix |
| `gvca` always 0 | Modbus TCP connection failed | Check `ping 192.168.1.1` |
| Gripper doesn't release on Ctrl+C | Shutdown sequence missing (fixed) | Rebuild after fix |
