import rclpy
from rclpy.node import Node
import tkinter as tk
import threading
import subprocess
import time

class ConveyorUI(Node):
    def __init__(self):
        super().__init__('conveyor_ui')
        self.is_moving = False
        
        # Start the background logic loop
        self.control_thread = threading.Thread(target=self.conveyor_loop, daemon=True)
        self.control_thread.start()

    def send_belt_speed(self, speed):
        # Talk directly to Gazebo physics for maximum stability
        topic = "/model/conveyor_belt_model/link/belt_link/track_cmd_vel"
        cmd = ["gz", "topic", "-t", topic, "-m", "gz.msgs.Double", "-p", f"data: {speed}"]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def build_ui(self):
        self.root = tk.Tk()
        self.root.title("Conveyor Belt Control")
        self.root.geometry("380x360") # Slightly taller to fit new buttons
        
        # DIRECTION TOGGLE
        tk.Label(self.root, text="Belt Direction:", font=("Arial", 10, "bold")).pack(pady=2)
        self.dir_var = tk.IntVar(value=-1) # Default to -1 (Towards Arm)
        frame = tk.Frame(self.root)
        frame.pack()
        tk.Radiobutton(frame, text="Towards Arm (-)", variable=self.dir_var, value=-1).pack(side=tk.LEFT, padx=10)
        tk.Radiobutton(frame, text="Away from Arm (+)", variable=self.dir_var, value=1).pack(side=tk.LEFT, padx=10)

        tk.Label(self.root, text="Belt Speed (m/s):", font=("Arial", 10, "bold")).pack(pady=2)
        self.speed_var = tk.DoubleVar(value=0.5)
        tk.Scale(self.root, variable=self.speed_var, from_=0.1, to=2.0, resolution=0.1, orient=tk.HORIZONTAL, length=200).pack()

        tk.Label(self.root, text="Shift Distance (meters):", font=("Arial", 10, "bold")).pack(pady=2)
        self.dist_var = tk.DoubleVar(value=0.5)
        tk.Scale(self.root, variable=self.dist_var, from_=0.1, to=2.0, resolution=0.1, orient=tk.HORIZONTAL, length=200).pack()

        tk.Label(self.root, text="Wait/Pause Time (seconds):", font=("Arial", 10, "bold")).pack(pady=2)
        self.pause_var = tk.DoubleVar(value=2.0)
        tk.Scale(self.root, variable=self.pause_var, from_=0.5, to=5.0, resolution=0.5, orient=tk.HORIZONTAL, length=200).pack()

        self.btn_toggle = tk.Button(self.root, text="START BELT", bg="green", fg="white", font=("Arial", 12, "bold"), command=self.toggle_belt)
        self.btn_toggle.pack(pady=15)
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()

    def toggle_belt(self):
        self.is_moving = not self.is_moving
        if self.is_moving:
            self.btn_toggle.config(text="STOP BELT", bg="red")
        else:
            self.btn_toggle.config(text="START BELT", bg="green")
            self.send_belt_speed(0.0) # Emergency stop

    def conveyor_loop(self):
        while rclpy.ok():
            if self.is_moving:
                # Multiply speed by the direction variable (1 or -1)
                speed = self.speed_var.get() * self.dir_var.get()
                distance = self.dist_var.get()
                pause = self.pause_var.get()
                
                # 1. Move the belt
                self.send_belt_speed(speed)
                time.sleep(distance / abs(speed)) # Time = Distance / Speed
                
                # 2. Stop the belt
                self.send_belt_speed(0.0)
                
                # 3. Wait before next shift
                for _ in range(int(pause * 10)):
                    if not self.is_moving: break
                    time.sleep(0.1)
            else:
                time.sleep(0.1)

    def on_closing(self):
        self.is_moving = False
        self.send_belt_speed(0.0)
        self.root.destroy()
        rclpy.shutdown()

def main():
    rclpy.init()
    node = ConveyorUI()
    
    spin_thread = threading.Thread(target=rclpy.spin, args=(node,), daemon=True)
    spin_thread.start()
    
    node.build_ui() 

if __name__ == '__main__':
    main()