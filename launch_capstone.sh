#!/bin/bash
echo "Cleaning up zombie processes from previous runs..."
pkill -f gz
pkill -f ros2
pkill -f spawner
pkill -f ruby
pkill -f rqt
sleep 2 

export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
export GZ_SIM_RESOURCE_PATH=/home/mos/final_pro/the_last_dance/src

cd /home/mos/final_pro/the_last_dance
colcon build --symlink-install
source install/setup.bash

echo "Starting Phase 4: Full Simulation + Direct Joint Control..."

# Terminal 1: Gazebo Physics
gnome-terminal --tab --title="Gazebo World" -- bash -c "source install/setup.bash; export GZ_SIM_RESOURCE_PATH=/home/mos/final_pro/the_last_dance/src; ros2 launch ros_gz_sim gz_sim.launch.py gz_args:='/home/mos/final_pro/the_last_dance/src/my_capstone_brain/worlds/capstone_world.sdf -r'; exec bash"

sleep 4 

# Terminal 2: Robot State Publisher
gnome-terminal --tab --title="URDF Publisher" -- bash -c "source install/setup.bash; xacro /home/mos/final_pro/the_last_dance/src/mycobot_description/urdf/robots/mycobot_280.urdf.xacro use_gazebo:=\"true\" > /tmp/robot.urdf; ros2 run robot_state_publisher robot_state_publisher --ros-args -p robot_description:=\"\$(cat /tmp/robot.urdf)\" -p use_sim_time:=true; exec bash"

sleep 2 

# Terminal 3: Gazebo Spawner & Motor Controllers
gnome-terminal --tab --title="Gazebo Spawner" -- bash -c "source install/setup.bash; export GZ_SIM_RESOURCE_PATH=/home/mos/final_pro/the_last_dance/src; ros2 run ros_gz_sim create -topic robot_description -name mycobot -x -0.06 -y -0.05 -z 0.0; sleep 5; ros2 run controller_manager spawner joint_state_broadcaster --controller-manager-timeout 60; ros2 run controller_manager spawner arm_controller --controller-manager-timeout 60; ros2 run controller_manager spawner mycobot_gripper_controller --controller-manager-timeout 60; exec bash"

# Terminal 4: Vision Bridge (CAMERA FIXED HERE!)
gnome-terminal --tab --title="Vision Bridge" -- bash -c "source install/setup.bash; ros2 run ros_gz_bridge parameter_bridge /overhead_camera/image_raw@sensor_msgs/msg/Image[gz.msgs.Image] & ros2 run rqt_image_view rqt_image_view; exec bash"

# Terminal 5: Box Spawner
gnome-terminal --tab --title="Box Spawner" -- bash -c "source install/setup.bash; ros2 run my_capstone_brain spawner_node; exec bash"

# Terminal 6: Conveyor UI
gnome-terminal --tab --title="Conveyor UI" -- bash -c "source install/setup.bash; ros2 run my_capstone_brain conveyor_node; exec bash"

# Terminal 7: Keyboard FK Control (SWAPPED FROM IK TO FK)
gnome-terminal --tab --title="Keyboard Control" -- bash -c "source install/setup.bash; echo 'Waiting for controllers to start...'; sleep 10; ros2 run my_capstone_brain fk_teleop_node; exec bash"