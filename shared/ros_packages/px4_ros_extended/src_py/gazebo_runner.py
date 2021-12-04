#!/usr/bin/env python3
import subprocess
import numpy as np
import rclpy
import time
import argparse

# ROS dep
from px4_msgs.msg import VehicleOdometry
from std_msgs.msg import Int64


class GazeboRunnerNode:
    def __init__(self, node, train=True):
        self.node = node

        self.vehicle_odometry_subscriber = self.node.create_subscription(VehicleOdometry, '/fmu/vehicle_odometry/out',
                                                                         self.vehicle_odometry_callback, 1)
        self.resetting_publisher = self.node.create_publisher(Int64, '/env/resetting', 1)

        # Look for "connection closed by client"
        self.timer_check_connection = self.node.create_timer(1, self.check_connection)  # 1Hz

        self.train = train
        self.cont_takeoff_failing = 0
        self.state = []
        self.gazebo = None
        self.started = False
        self.msg_reset_gazebo = Int64()
        self.start_gazebo()
        self.start_time_no_connection = time.time()  # Used to catch stalled trainig due to "connection closed by client"

    def vehicle_odometry_callback(self, obs):
        self.state = [obs.x, obs.y, obs.z, obs.vx, obs.vy, obs.vz]
        if np.abs(self.state[2]) <= 0.6 and self.started:
            self.cont_takeoff_failing += 1
            if self.cont_takeoff_failing >= 2000:
                self.kill_gazebo()
                self.start_gazebo()
        elif np.abs(self.state[2]) <= 0.6 and not self.started:
            self.msg_reset_gazebo.data = 0  # Signaling to env that gazebo is ready
            self.resetting_publisher.publish(self.msg_reset_gazebo)
        else:
            self.started = True
            self.cont_takeoff_failing = 0
        self.start_time_no_connection = time.time()  # Resetting time without connection

    def start_gazebo(self):
        self.started = False

        if self.train:
            self.gazebo = subprocess.Popen(["make", "px4_sitl_rtps", "gazebo", "PX4_SIM_SPEED_FACTOR=6", "HEADLESS=1"], cwd="/src/PX4-Autopilot")
        else:
            self.gazebo = subprocess.Popen(["make", "px4_sitl_rtps", "gazebo", "PX4_NO_FOLLOW_MODE=1"], cwd="/src/PX4-Autopilot")
        time.sleep(5)
        self.cont_takeoff_failing = 0
        self.msg_reset_gazebo.data = 0  # Signaling to env that gazebo is ready
        self.resetting_publisher.publish(self.msg_reset_gazebo)
        self.start_time_no_connection = time.time()  # Resetting time without connection

    def kill_gazebo(self):
        self.msg_reset_gazebo.data = 1  # Signaling to env that gazebo is resetting
        self.resetting_publisher.publish(self.msg_reset_gazebo)
        self.gazebo.kill()
        time.sleep(1)

    def check_connection(self):
        if time.time() - self.start_time_no_connection > 5.0:
            self.kill_gazebo()
            self.start_gazebo()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    feature_parser = parser.add_mutually_exclusive_group(required=False)
    feature_parser.add_argument('--train', dest='train', action='store_true')
    feature_parser.add_argument('--test', dest='train', action='store_false')
    parser.set_defaults(train=True)
    args = parser.parse_args()

    rclpy.init(args=None)
    m_node = rclpy.create_node('gazebo_runner_node')
    gsNode = GazeboRunnerNode(m_node, args.train)
    rclpy.spin(m_node)
