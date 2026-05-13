import rclpy
from rclpy.node import Node
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from builtin_interfaces.msg import Duration
import sys, select, termios, tty, threading
import numpy as np

class FKTeleopNode(Node):
    def __init__(self):
        super().__init__('fk_teleop_node')
        self.arm_pub = self.create_publisher(JointTrajectory, '/arm_controller/joint_trajectory', 10)
        self.gripper_pub = self.create_publisher(JointTrajectory, '/mycobot_gripper_controller/joint_trajectory', 10)
        
        self.joint_names = [
            'link1_to_link2', 'link2_to_link3', 'link3_to_link4',
            'link4_to_link5', 'link5_to_link6', 'link6_to_link6_flange'
        ]
        
        self.current_joints = np.zeros(6)
        self.current_gripper_pos = 0.0 # Start fully open
        
        self.settings = termios.tcgetattr(sys.stdin)
        self.get_logger().info("\n==================================")
        self.get_logger().info("JOINT TELEOP (FK) READY!")
        self.get_logger().info("Q / A : Joint 1 (Base Yaw)")
        self.get_logger().info("W / S : Joint 2 (Shoulder Pitch)")
        self.get_logger().info("E / D : Joint 3 (Elbow Pitch)")
        self.get_logger().info("R / F : Joint 4 (Wrist Pitch)")
        self.get_logger().info("T / G : Joint 5 (Wrist Yaw)")
        self.get_logger().info("Y / H : Joint 6 (Wrist Roll)")
        self.get_logger().info("U / J : Gripper (Open / Close)")
        self.get_logger().info("==================================\n")

        self.input_thread = threading.Thread(target=self.keyboard_loop, daemon=True)
        self.input_thread.start()

    def publish_joints(self):
        msg = JointTrajectory()
        msg.joint_names = self.joint_names
        point = JointTrajectoryPoint()
        point.positions = self.current_joints.tolist()
        point.time_from_start = Duration(sec=0, nanosec=500000000) # 0.5s move time
        msg.points.append(point)
        self.arm_pub.publish(msg)

    def publish_gripper(self):
        msg = JointTrajectory()
        msg.joint_names = ['gripper_controller']
        point = JointTrajectoryPoint()
        point.positions = [self.current_gripper_pos]
        # Faster reaction time for the gripper so you can tap the keys
        point.time_from_start = Duration(sec=0, nanosec=100000000) 
        msg.points.append(point)
        self.gripper_pub.publish(msg)

    def get_key(self):
        tty.setraw(sys.stdin.fileno())
        rlist, _, _ = select.select([sys.stdin], [], [], 0.1)
        if rlist:
            key = sys.stdin.read(1)
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.settings)
            return key.lower()
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.settings)
        return None

    def keyboard_loop(self):
        step = 0.05 
        while rclpy.ok():
            key = self.get_key()
            if key:
                # Arm Joints
                if key == 'q': self.current_joints[0] += step
                elif key == 'a': self.current_joints[0] -= step
                elif key == 'w': self.current_joints[1] += step
                elif key == 's': self.current_joints[1] -= step
                elif key == 'e': self.current_joints[2] += step
                elif key == 'd': self.current_joints[2] -= step
                elif key == 'r': self.current_joints[3] += step
                elif key == 'f': self.current_joints[3] -= step
                elif key == 't': self.current_joints[4] += step
                elif key == 'g': self.current_joints[4] -= step
                elif key == 'y': self.current_joints[5] += step
                elif key == 'h': self.current_joints[5] -= step
                
                # Gripper Controls
                elif key == 'u': 
                    self.current_gripper_pos += step
                    # URDF max open limit
                    self.current_gripper_pos = np.clip(self.current_gripper_pos, -0.7, 0.15)
                    self.publish_gripper()
                    print(f"Gripper Pos: {self.current_gripper_pos:.2f} (Opening)")
                elif key == 'j': 
                    self.current_gripper_pos -= step
                    # URDF max close limit
                    self.current_gripper_pos = np.clip(self.current_gripper_pos, -0.7, 0.15)
                    self.publish_gripper()
                    print(f"Gripper Pos: {self.current_gripper_pos:.2f} (Closing)")
                
                self.current_joints = np.clip(self.current_joints, -2.8, 2.8)
                
                if key not in ['u', 'j']:
                    print(f"Joints: {[round(j, 2) for j in self.current_joints]}")
                    self.publish_joints()

def main():
    rclpy.init()
    node = FKTeleopNode()
    node.publish_joints() 
    node.publish_gripper()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, node.settings)
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()