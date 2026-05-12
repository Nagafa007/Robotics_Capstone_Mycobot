import rclpy
from rclpy.node import Node
import subprocess
import time

class BoxSpawner(Node):
    def __init__(self):
        super().__init__('box_spawner')
        self.get_logger().info("Starting Procedural Box Spawner...")
        self.spawn_boxes()

    def spawn_boxes(self):
        colors = [
            ("Red", "1 0 0 1"),
            ("Green", "0 1 0 1"),
            ("Blue", "0 0 1 1")
        ]
        
        # Start at arm center (-0.06), spacing 0.5m apart
        start_x = -0.06 
        spacing_x = 0.5

        for i in range(10):
            color_name, rgba = colors[i % 3]
            box_x = start_x + (i * spacing_x)
            box_name = f"box_{i}_{color_name.lower()}"
            
            # Keep SDF pose at 0, we will inject real pose via command line
            box_sdf = f"""
            <?xml version="1.0" ?>
            <sdf version="1.8">
                <model name="{box_name}">
                    <pose>0 0 0 0 0 0</pose>
                    <link name="link">
                        <inertial><mass>0.05</mass></inertial>
                        <collision name="col"><geometry><box><size>0.04 0.04 0.04</size></box></geometry></collision>
                        <visual name="vis">
                            <geometry><box><size>0.04 0.04 0.04</size></box></geometry>
                            <material><ambient>{rgba}</ambient><diffuse>{rgba}</diffuse></material>
                        </visual>
                    </link>
                </model>
            </sdf>
            """
            
            with open("/tmp/temp_box.sdf", "w") as f:
                f.write(box_sdf)
                
            # FORCE the coordinates using -x, -y, -z arguments
            cmd = [
                "ros2", "run", "ros_gz_sim", "create", 
                "-file", "/tmp/temp_box.sdf", 
                "-name", box_name,
                "-x", str(box_x),
                "-y", "0.23",
                "-z", "0.15"
            ]
            
            subprocess.run(cmd, stdout=subprocess.DEVNULL)
            self.get_logger().info(f"Spawned {color_name} box at X: {box_x}")
            time.sleep(0.1)

def main():
    rclpy.init()
    node = BoxSpawner()
    rclpy.shutdown()

if __name__ == '__main__':
    main()