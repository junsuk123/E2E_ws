#!/usr/bin/env python3
# File: e2e_ws/src/data_collector/data_collector/collector_node.py

import os
import csv
from datetime import datetime

import cv2
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from geometry_msgs.msg import Twist
from cv_bridge import CvBridge
from ament_index_python.packages import get_package_share_directory

class CollectorNode(Node):
    def __init__(self):
        super().__init__('data_collector')
        self.bridge = CvBridge()
        self.latest_twist = None

        # 1) 패키지의 share 디렉터리 경로를 자동으로 찾는다
        pkg_share = get_package_share_directory('data_collector')
        # 2) 그 아래 data 폴더를 기준으로
        data_base = os.path.join(pkg_share, 'data')
        # 3) 날짜·시간 기반 서브폴더 이름 생성
        now_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        default_dir = os.path.join(data_base, now_str)

        # 파라미터로 덮어쓰기 가능하지만, 기본(default_dir)만으로도 동작
        self.out_dir = self.declare_parameter('out_dir', default_dir).value
        os.makedirs(self.out_dir, exist_ok=True)

        # CSV 경로 및 헤더 작성
        self.csv_path = os.path.join(self.out_dir, 'data.csv')
        with open(self.csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['timestamp', 'image_file', 'linear_x', 'angular_z'])

        # 구독 설정
        self.create_subscription(Twist, 'cmd_vel', self.twist_cb, 10)
        self.create_subscription(Image, 'fused_image', self.image_cb, 10)

        self.get_logger().info(f"Saving dataset under: {self.out_dir}")

    def twist_cb(self, msg: Twist):
        self.latest_twist = msg

    def image_cb(self, img_msg: Image):
        if self.latest_twist is None:
            self.get_logger().warn("No cmd_vel yet; skipping this frame")
            return

        ts = img_msg.header.stamp.sec + img_msg.header.stamp.nanosec * 1e-9
        fname = f"{ts:.6f}.png"
        img_path = os.path.join(self.out_dir, fname)

        # 이미지 저장
        cv_img = self.bridge.imgmsg_to_cv2(img_msg, 'bgr8')
        cv2.imwrite(img_path, cv_img)

        # CSV에 기록
        with open(self.csv_path, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                f"{ts:.6f}",
                fname,
                f"{self.latest_twist.linear.x:.4f}",
                f"{self.latest_twist.angular.z:.4f}"
            ])

        self.get_logger().info(
            f"Saved {fname}  vx={self.latest_twist.linear.x:.2f}  wz={self.latest_twist.angular.z:.2f}"
        )

def main(args=None):
    rclpy.init(args=args)
    node = CollectorNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
