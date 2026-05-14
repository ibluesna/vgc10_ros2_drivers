#!/usr/bin/env python3

import time
import rclpy
import vgc10_modbus_tcp.comModbusTcp
import vgc10_control.baseOnRobotVG
from vgc10_msgs.msg import OnRobotVGInput
from vgc10_msgs.msg import OnRobotVGOutput
import threading


def main():
    try:
        rclpy.init()
        node = rclpy.create_node("OnRobotVGTcpNode")
        node.declare_parameter('/onrobot/ip', '192.168.0.4')
        node.declare_parameter('/onrobot/port', '50002')
        node.declare_parameter('/onrobot/dummy', False)


        ip = node.get_parameter('/onrobot/ip').value
        port = int(node.get_parameter('/onrobot/port').value)
        dummy = node.get_parameter('/onrobot/dummy').value

        # Gripper is a VG gripper with a Modbus/TCP connection
        gripper = vgc10_control.baseOnRobotVG.onrobotbaseVG()
        gripper.client = vgc10_modbus_tcp.comModbusTcp.communication(dummy)

        # Connects to the ip address received as an argument
        gripper.client.connectToDevice(ip, port)

        # The Gripper status is published on the topic named 'OnRobotVGInput'
        pub = node.create_publisher(OnRobotVGInput, 'OnRobotVGInput', 1)

        # The Gripper command is received from the topic named 'OnRobotVGOutput'
        subscription = node.create_subscription(OnRobotVGOutput, 'OnRobotVGOutput', gripper.refreshCommand, 10)

        # Spin in a separate thread (once, outside the loop)
        thread = threading.Thread(target=rclpy.spin, args=(node, ), daemon=True)
        thread.start()

        # We loop
        prev_msg = []
        rate = node.create_rate(20)  # 20 Hz
        while rclpy.ok():
            # Get and publish the Gripper status
            status = gripper.getStatus()
            pub.publish(status)

            rate.sleep()
            # Send the most recent command
            if not prev_msg == gripper.message:  # find new message
                node.get_logger().info("Sending message.")
                gripper.sendCommand()
                prev_msg = list(gripper.message)
    except KeyboardInterrupt:
        node.get_logger().info("Shutting down: releasing gripper...")
        release = OnRobotVGOutput()
        release.rmca = 0
        release.rvca = 0
        release.rmcb = 0
        release.rvcb = 0
        gripper.refreshCommand(release)
        gripper.sendCommand()
        time.sleep(0.5)
        gripper.client.disconnectFromDevice()
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()