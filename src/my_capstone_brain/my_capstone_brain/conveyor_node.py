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
        self.control_thread = threading.Thread(target=self.conveyor_loop, daemon=True)
        self.control_thread.start()

    def send_belt_speed(self, speed):
        topic = "/model/conveyor_belt_model/link/belt_link/track_cmd_vel"
        cmd = ["gz", "topic", "-t", topic, "-m", "gz.msgs.Double", "-p", f"data: {speed}"]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def build_ui(self):
        self.root = tk.Tk()
        self.root.title("Conveyor Belt Control")
        self.root.geometry("420x450") 
        
        # --- AUTO SEQUENCE SECTION ---
        tk.Label(self.root, text="--- AUTO SEQUENCE ---", font=("Arial", 10, "bold"), fg="blue").pack(pady=(10, 0))
        
        tk.Label(self.root, text="Belt Direction:", font=("Arial", 9)).pack(pady=2)
        self.dir_var = tk.IntVar(value=-1)
        frame = tk.Frame(self.root)
        frame.pack()
        tk.Radiobutton(frame, text="Towards Arm (-)", variable=self.dir_var, value=-1).pack(side=tk.LEFT, padx=10)
        tk.Radiobutton(frame, text="Away from Arm (+)", variable=self.dir_var, value=1).pack(side=tk.LEFT, padx=10)

        tk.Label(self.root, text="Belt Speed (m/s):", font=("Arial", 9)).pack(pady=2)
        self.speed_var = tk.DoubleVar(value=0.5)
        tk.Scale(self.root, variable=self.speed_var, from_=0.1, to=2.0, resolution=0.1, orient=tk.HORIZONTAL, length=200).pack()

        tk.Label(self.root, text="Shift Distance (meters):", font=("Arial", 9)).pack(pady=2)
        self.dist_var = tk.DoubleVar(value=0.5)
        tk.Scale(self.root, variable=self.dist_var, from_=0.1, to=2.0, resolution=0.1, orient=tk.HORIZONTAL, length=200).pack()

        tk.Label(self.root, text="Wait/Pause Time (seconds):", font=("Arial", 9)).pack(pady=2)
        self.pause_var = tk.DoubleVar(value=2.0)
        tk.Scale(self.root, variable=self.pause_var, from_=0.5, to=5.0, resolution=0.5, orient=tk.HORIZONTAL, length=200).pack()

        self.btn_toggle = tk.Button(self.root, text="START AUTO BELT", bg="green", fg="white", font=("Arial", 11, "bold"), command=self.toggle_belt)
        self.btn_toggle.pack(pady=10)

        # --- MANUAL OFFSET / NUDGE SECTION ---
        tk.Label(self.root, text="--- MANUAL OFFSET / NUDGE ---", font=("Arial", 10, "bold"), fg="purple").pack(pady=(15, 0))
        tk.Label(self.root, text="Nudge Distance (meters):", font=("Arial", 9)).pack(pady=2)
        self.nudge_var = tk.DoubleVar(value=0.05) # 5 cm default
        tk.Scale(self.root, variable=self.nudge_var, from_=0.01, to=0.3, resolution=0.01, orient=tk.HORIZONTAL, length=200).pack()
        
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=5)
        tk.Button(btn_frame, text="<< Nudge Towards Arm", bg="lightgrey", command=lambda: self.nudge_belt(-1)).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Nudge Away >>", bg="lightgrey", command=lambda: self.nudge_belt(1)).pack(side=tk.LEFT, padx=5)
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()

    def nudge_belt(self, direction):
        if self.is_moving:
            print("Cannot nudge while AUTO sequence is running!")
            return
        
        dist = self.nudge_var.get()
        speed = 0.2 * direction # Gentle speed for fine alignment
        
        def run_nudge():
            self.send_belt_speed(speed)
            time.sleep(dist / abs(speed))
            self.send_belt_speed(0.0)
            
        # Run in a thread so it doesn't freeze the UI buttons
        threading.Thread(target=run_nudge, daemon=True).start()

    def toggle_belt(self):
        self.is_moving = not self.is_moving
        if self.is_moving:
            self.btn_toggle.config(text="STOP AUTO BELT", bg="red")
        else:
            self.btn_toggle.config(text="START AUTO BELT", bg="green")
            self.send_belt_speed(0.0)

    def conveyor_loop(self):
        while rclpy.ok():
            if self.is_moving:
                speed = self.speed_var.get() * self.dir_var.get()
                distance = self.dist_var.get()
                pause = self.pause_var.get()
                
                self.send_belt_speed(speed)
                time.sleep(distance / abs(speed))
                self.send_belt_speed(0.0)
                
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