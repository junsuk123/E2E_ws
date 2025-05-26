#!/usr/bin/env python3
import math
import numpy as np
import cv2
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from sensor_msgs.msg import Image
from yolo_msgs.msg import DetectionArray
from cv_bridge import CvBridge

def quaternion_to_yaw(qx, qy, qz, qw):
    # from quaternion to yaw (rad)
    return math.atan2(2.0*(qw*qz + qx*qy),
                      1.0 - 2.0*(qy*qy + qz*qz))

class ImageFusionNode(Node):
    def __init__(self):
        super().__init__('image_fusion_node')
        self.bridge = CvBridge()
        self.twist = Twist()
        self.odom = Odometry()
        self.detections = DetectionArray()
        self.pub = self.create_publisher(Image, 'fused_image', 10)

        self.create_subscription(Twist, 'cmd_vel', self.cmd_vel_cb, 10)
        self.create_subscription(Odometry, 'odom', self.odom_cb, 10)
        self.create_subscription(DetectionArray, 'yolo/detections',
                                 self.detections_cb, 10)

        rate = self.declare_parameter('update_rate', 10.0).value
        self.create_timer(1.0/ rate, self.timer_cb)

    def cmd_vel_cb(self, msg: Twist):
        self.twist = msg

    def odom_cb(self, msg: Odometry):
        self.odom = msg

    def detections_cb(self, msg: DetectionArray):
        self.detections = msg

    def timer_cb(self):
        # 1) 빈 캔버스
        img = np.zeros((320, 320, 3), dtype=np.uint8)

        # 2) cmd_vel 영역 (상단 높이=80px)
        lin = max(0.0, min(5.0, self.twist.linear.x))
        ang = self.twist.angular.z  # rad/sec treated as steering

        # 선속도 bar (blue)
        bar_len = int((lin / 5.0) * 320)
        cv2.rectangle(img, (0, 0), (bar_len, 20), (255, 0, 0), cv2.FILLED)

        # 각속도 line (red)
        angle_deg = math.degrees(ang)
        center_x = 160
        line_x = int(center_x + (angle_deg/180.0) * 160)
        cv2.line(img, (center_x, 40), (line_x, 40), (0, 0, 255), 3)
        # 3) 장애물 bounding box (녹색)
        for det in self.detections.detections:
            if det.score < 0.5:
                continue
            # scale from original 640x480 → 320x240 + 80 offset
            scale_x, scale_y = 0.5, 0.5
            cx = int(det.bbox.center.position.x * scale_x)
            cy = int(det.bbox.center.position.y * scale_y) + 80
            w = int(det.bbox.size.x * scale_x)
            h = int(det.bbox.size.y * scale_y)
            x0 = max(0, cx - w // 2)
            y0 = max(80, cy - h // 2)
            cv2.rectangle(img, (x0, y0), (x0 + w, y0 + h), (0, 255, 0), 2)

        # 4) 자세 arrow (purple)
        # 삼각형 포인트 (upward)
        pts = np.array([[0, -30], [-15, 10], [15, 10]], np.float32)
        # 회전
        q = self.odom.pose.pose.orientation
        yaw = (-1)*quaternion_to_yaw(q.x, q.y, q.z, q.w)
        R = np.array([[math.cos(yaw), -math.sin(yaw)],
                      [math.sin(yaw),  math.cos(yaw)]], np.float32)
        rot_pts = np.dot(pts, R.T).astype(np.int32)
        # 위치
        base = np.array([160, 280], np.int32)
        tri_pts = (rot_pts + base).reshape((-1,1,2))
        cv2.fillPoly(img, [tri_pts], (255, 0, 255))

        # 퍼블리시
        out = self.bridge.cv2_to_imgmsg(img, encoding='bgr8')
        out.header.stamp = self.get_clock().now().to_msg()
        self.pub.publish(out)

def main(args=None):
    rclpy.init(args=args)
    node = ImageFusionNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()
