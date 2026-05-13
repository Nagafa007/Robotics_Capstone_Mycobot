import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2
import numpy as np

class VisionNode(Node):
    def __init__(self):
        super().__init__('vision_node')
        self.subscription = self.create_subscription(
            Image,
            '/overhead_camera/image_raw',
            self.image_callback,
            10)
        self.bridge = CvBridge()
        self.get_logger().info("Vision Node Active. Waiting for camera feed...")

    def image_callback(self, msg):
        try:
            # Convert ROS Image to OpenCV BGR format
            cv_image = self.bridge.imgmsg_to_cv2(msg, "bgr8")
        except Exception as e:
            self.get_logger().error(f"Image conversion failed: {e}")
            return

        # Convert to HSV color space
        hsv = cv2.cvtColor(cv_image, cv2.COLOR_BGR2HSV)

        # Widened the red mask significantly to account for Gazebo lighting/shadows
        lower_red1 = np.array([0, 70, 50])
        upper_red1 = np.array([10, 255, 255])
        lower_red2 = np.array([160, 70, 50])
        upper_red2 = np.array([180, 255, 255])

        mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
        mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
        red_mask = mask1 + mask2

        contours, _ = cv2.findContours(red_mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        red_detected = False
        for contour in contours:
            # FIXED: Lowered the area threshold from 500 to 100 to catch the small cubes!
            if cv2.contourArea(contour) > 100: 
                x, y, w, h = cv2.boundingRect(contour)
                
                # Draw the bounding box
                cv2.rectangle(cv_image, (x, y), (x + w, y + h), (0, 0, 255), 2)
                
                # Calculate the precise center of the cube
                cx = x + (w // 2)
                cy = y + (h // 2)
                
                # Draw a white targeting dot in the exact center
                cv2.circle(cv_image, (cx, cy), 3, (255, 255, 255), -1)
                
                # Display the Pixel Coordinates
                cv2.putText(cv_image, f"TARGET ({cx},{cy})", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
                red_detected = True

        if red_detected:
            cv2.putText(cv_image, "STATUS: RED CUBE DETECTED", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        else:
            cv2.putText(cv_image, "STATUS: SCANNING...", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)

        cv2.imshow("Overhead Vision System", cv_image)
        cv2.waitKey(1)

def main():
    rclpy.init()
    node = VisionNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        cv2.destroyAllWindows()
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()