#!/usr/bin/env python

import rospy
from std_msgs.msg import ColorRGBA
from sensor_msgs.msg import LaserScan
from drive_msgs.msg import drive_param

from rviz_geometry import show_circle_in_rviz, show_line_in_rviz

import circle
from circle import Point

import math

import numpy as np

TOPIC_DRIVE_PARAMETERS = "/input/drive_param/autonomous"
TOPIC_LASER_SCAN = "/scan"

UPDATE_FREQUENCY = 60

last_speed = 0

DEFAULT_PARAMETERS = {
    'min_throttle': 0.2,
    'max_throttle': 1.0,

    'radius_lower': 2,
    'radius_upper': 30,

    'steering_slow_down': 4,
    'steering_slow_down_dead_zone': 0.2,

    'high_speed_steering_limit': 0.5,
    'high_speed_steering_limit_dead_zone': 0.2,

    'max_acceleration': 0.4,

    'corner_cutting': 1.4,
    'straight_smoothing': 1.0,

    'barrier_size_realtive': 0.1,
    'barrier_lower_limit': 1,
    'barrier_upper_limit': 15,
    'barrier_exponent': 1.4,

    'controller_p': 4,
    'controller_i': 0.2,
    'controller_d': 0.02
}

class Parameters():
    def __init__(self, default_values):
        self.names = default_values.keys()
        for name in self.names:
            setattr(self, name, default_values[name])

    def load(self):
        for name in self.names:
            default = getattr(self, name)
            value = rospy.get_param("wallfollowing/" + name, default)
            setattr(self, name, value)



class PIDController():
    def __init__(self, p, i, d, anti_windup=0.2):
        self.p = p
        self.i = i
        self.d = d
        self.anti_windup = anti_windup

        self.integral = 0
        self.previous_error = 0

    def update_and_get_correction(self, error, delta_time):
        self.integral += error * delta_time
        if self.integral > self.anti_windup:
            self.integral = self.anti_windup
        elif self.integral < -self.anti_windup:
            self.integral = -self.anti_windup

        derivative = (error - self.previous_error) / delta_time
        self.previous_error = error
        return self.p * error + self.i * self.integral + self.d * derivative


def map(in_lower, in_upper, out_lower, out_upper, value):
    result = out_lower + (out_upper - out_lower) * \
        (value - in_lower) / (in_upper - in_lower)
    return min(out_upper, max(out_lower, result))


def drive(angle, velocity):
    message = drive_param()
    message.angle = angle
    message.velocity = velocity
    drive_parameters_publisher.publish(message)


def laser_callback(message):
    global laser_scan
    laser_scan = message


def get_scan_as_cartesian():
    if laser_scan is None:
        raise Exception("No scan has been received yet.")

    ranges = np.array(laser_scan.ranges)

    inf_mask = np.isinf(ranges)
    if inf_mask.any():
        ranges = ranges[~inf_mask]

    angles = np.linspace(
        laser_scan.angle_min,
        laser_scan.angle_max,
        ranges.shape[0])

    points = np.zeros((ranges.shape[0], 2))
    points[:, 0] = -np.sin(angles) * ranges
    points[:, 1] = np.cos(angles) * ranges

    return points


def find_left_right_border(points, margin_relative=0.1):
    margin = int(points.shape[0] * margin_relative)

    relative = points[margin + 1:-margin, :] - points[margin:-margin - 1, :]
    distances = np.linalg.norm(relative, axis=1)

    return margin + np.argmax(distances) + 1


def follow_walls(left_circle, right_circle, barrier):
    global last_speed

    prediction_distance = parameters.corner_cutting + parameters.straight_smoothing * last_speed

    predicted_car_position = Point(0, prediction_distance)
    left_point = left_circle.get_closest_point(predicted_car_position)
    right_point = right_circle.get_closest_point(predicted_car_position)

    target_position = Point(
        (left_point.x + right_point.x) / 2,
        (left_point.y + right_point.y) / 2)
    error = (target_position.x - predicted_car_position.x) / prediction_distance
    if math.isnan(error) or math.isinf(error):
        error = 0

    steering_angle = pid.update_and_get_correction(
        error, 1.0 / UPDATE_FREQUENCY)

    radius = min(left_circle.radius, right_circle.radius)
    speed_limit_radius = map(parameters.radius_lower, parameters.radius_upper, 0, 1, radius)
    speed_limit_error = max(0, 1 + parameters.steering_slow_down_dead_zone - abs(error) * parameters.steering_slow_down)  # nopep8
    speed_limit_acceleration = last_speed + parameters.max_acceleration / UPDATE_FREQUENCY
    speed_limit_barrier = map(parameters.barrier_lower_limit, parameters.barrier_upper_limit, 0, 1, barrier) ** parameters.barrier_exponent

    relative_speed = min(
        speed_limit_error,
        speed_limit_radius,
        speed_limit_acceleration,
        speed_limit_barrier
    )
    last_speed = relative_speed
    speed = map(0, 1, parameters.min_throttle, parameters.max_throttle, relative_speed)
    steering_angle = steering_angle * map(parameters.high_speed_steering_limit_dead_zone, 1, 1, parameters.high_speed_steering_limit, relative_speed)
    drive(steering_angle, speed)

    show_line_in_rviz(2, [left_point, right_point],
                      color=ColorRGBA(1, 1, 1, 0.3), line_width=0.005)
    show_line_in_rviz(3, [Point(0, 0), predicted_car_position],
                      color=ColorRGBA(1, 1, 1, 0.3), line_width=0.005)
    show_line_in_rviz(4, [predicted_car_position,
                          target_position], color=ColorRGBA(1, 0.4, 0, 1))

    
    show_line_in_rviz(5, [Point(-2, barrier),
                          Point( 2, barrier),], color=ColorRGBA(1, 1, 0, 1))


def handle_scan():
    if laser_scan is None:
        return

    points = get_scan_as_cartesian()
    split = find_left_right_border(points)

    right_wall = points[:split:4, :]
    left_wall = points[split::4, :]

    left_circle = circle.fit(left_wall)
    right_circle = circle.fit(right_wall)

    barrier_start = int(points.shape[0] * (0.5 - parameters.barrier_size_realtive))
    barrier_end = int(points.shape[0] * (0.5 + parameters.barrier_size_realtive))
    barrier = np.max(points[barrier_start : barrier_end, 1])
    
    follow_walls(left_circle, right_circle, barrier)

    show_circle_in_rviz(left_circle, left_wall, 0)
    show_circle_in_rviz(right_circle, right_wall, 1)


laser_scan = None

rospy.Subscriber(TOPIC_LASER_SCAN, LaserScan, laser_callback)
drive_parameters_publisher = rospy.Publisher(
    TOPIC_DRIVE_PARAMETERS, drive_param, queue_size=1)

rospy.init_node('wallfollowing', anonymous=True)

parameters = Parameters(DEFAULT_PARAMETERS)
parameters.load()

timer = rospy.Rate(UPDATE_FREQUENCY)

pid = PIDController(parameters.controller_p, parameters.controller_i, parameters.controller_d)

while not rospy.is_shutdown():
    handle_scan()
    timer.sleep()
