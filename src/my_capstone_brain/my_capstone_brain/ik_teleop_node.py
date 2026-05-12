import rclpy
from rclpy.node import Node
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from builtin_interfaces.msg import Duration
import sys, select, termios, tty, threading
import numpy as np
from scipy.optimize import minimize

class IKTeleopNode(Node):
    def __init__(self):
        super().__init__('ik_teleop_node')
        # Arm Publisher
        self.arm_pub = self.create_publisher(JointTrajectory, '/arm_controller/joint_trajectory', 10)
        # Gripper Publisher
        self.gripper_pub = self.create_publisher(JointTrajectory, '/mycobot_gripper_controller/joint_trajectory', 10)
        
        # Start above the belt
        self.target_xyz = np.array([-0.06, 0.15, 0.20]) 
        self.current_joints = np.zeros(6)
        self.gripper_closed = False
        
        self.joint_names = [
            'link1_to_link2', 'link2_to_link3', 'link3_to_link4',
            'link4_to_link5', 'link5_to_link6', 'link6_to_link6_flange'
        ]
        
        self.settings = termios.tcgetattr(sys.stdin)
        self.get_logger().info("\n==================================")
        self.get_logger().info("IK TELEOP READY!")
        self.get_logger().info("ARROWS : Move X/Y (Forward/Back/Left/Right)")
        self.get_logger().info("W / S  : Move Z (Up/Down)")
        self.get_logger().info("G      : Toggle Gripper (Open/Close)")
        self.get_logger().info("==================================\n")

        self.input_thread = threading.Thread(target=self.keyboard_loop, daemon=True)
        self.input_thread.start()

    def forward_kinematics(self, q):
        # Approximate Mycobot lengths
        d1, a2, a3, d4, d5, d6 = 0.131, 0.110, 0.096, 0.064, 0.073, 0.045
        
        # Position calculation
        x = np.cos(q[0]) * (a2 * np.cos(q[1]) + a3 * np.cos(q[1]+q[2]))
        y = np.sin(q[0]) * (a2 * np.cos(q[1]) + a3 * np.cos(q[1]+q[2]))
        z = d1 - a2 * np.sin(q[1]) - a3 * np.sin(q[1]+q[2])
        
        x += np.cos(q[0]) * np.cos(q[1]+q[2]+q[3]) * (d4 + d5 + d6)
        y += np.sin(q[0]) * np.cos(q[1]+q[2]+q[3]) * (d4 + d5 + d6)
        z -= np.sin(q[1]+q[2]+q[3]) * (d4 + d5 + d6)
        
        # We also return the sum of the pitch joints to enforce orientation
        pitch_sum = q[1] + q[2] + q[3]
        return np.array([x, y, z]), pitch_sum

    def ik_cost(self, q):
        pos, pitch_sum = self.forward_kinematics(q)
        distance_error = np.linalg.norm(pos - self.target_xyz)
        
        # STRICT RULE: Pitch joints must sum to -pi/2 so gripper points straight down
        orientation_error = (pitch_sum - (-1.5708))**2 
        
        # STRICT RULE: Wrist yaw and roll (q4, q5) should stay at 0
        twist_error = q[4]**2 + q[5]**2
        
        return distance_error + (50.0 * orientation_error) + (10.0 * twist_error)

    def solve_ik_and_publish(self):
        # Constrain the target so it physically cannot go out of bounds
        self.target_xyz[0] = np.clip(self.target_xyz[0], -0.28, 0.28) # Max Reach X
        self.target_xyz[1] = np.clip(self.target_xyz[1], -0.28, 0.28) # Max Reach Y
        self.target_xyz[2] = np.clip(self.target_xyz[2], 0.05, 0.35)  # Safe Z (Don't hit belt)
        
        res = minimize(self.ik_cost, self.current_joints, bounds=[(-2.8, 2.8)]*6)
        self.current_joints = res.x
        
        # Publish Arm
        msg = JointTrajectory()
        msg.joint_names = self.joint_names
        point = JointTrajectoryPoint()
        point.positions = self.current_joints.tolist()
        point.time_from_start = Duration(sec=1, nanosec=0)
        msg.points.append(point)
        self.arm_pub.publish(msg)

    def toggle_gripper(self):
        self.gripper_closed = not self.gripper_closed
        target_pos = -0.7 if self.gripper_closed else 0.0 # -0.7 is closed, 0.0 is open
        
        msg = JointTrajectory()
        msg.joint_names = ['gripper_controller']
        point = JointTrajectoryPoint()
        point.positions = [target_pos]
        point.time_from_start = Duration(sec=1, nanosec=0)
        msg.points.append(point)
        self.gripper_pub.publish(msg)
        
        state = "CLOSED" if self.gripper_closed else "OPEN"
        print(f"--- Gripper {state} ---")

    def get_key(self):
        tty.setraw(sys.stdin.fileno())
        rlist, _, _ = select.select([sys.stdin], [], [], 0.1)
        if rlist:
            key = sys.stdin.read(1)
            if key == '\x1b':
                sys.stdin.read(1) 
                key = sys.stdin.read(1) 
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.settings)
                if key == 'A': return 'UP'
                if key == 'B': return 'DOWN'
                if key == 'C': return 'RIGHT'
                if key == 'D': return 'LEFT'
            else:
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.settings)
                return key.lower()
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.settings)
        return None

    def keyboard_loop(self):
        step = 0.02 # Move 2cm per key press
        while rclpy.ok():
            key = self.get_key()
            if key:
                if key == 'RIGHT': self.target_xyz[0] += step
                elif key == 'LEFT': self.target_xyz[0] -= step
                elif key == 'UP': self.target_xyz[1] += step
                elif key == 'DOWN': self.target_xyz[1] -= step
                elif key in ['w', 'q']: self.target_xyz[2] += step # Up
                elif key in ['s', 'e']: self.target_xyz[2] -= step # Down
                elif key == 'g': self.toggle_gripper()
                
                if key != 'g':
                    print(f"Target -> X: {self.target_xyz[0]:.2f}, Y: {self.target_xyz[1]:.2f}, Z: {self.target_xyz[2]:.2f}")
                    self.solve_ik_and_publish()

def main():
    rclpy.init()
    node = IKTeleopNode()
    node.solve_ik_and_publish() 
    
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