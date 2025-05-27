#!/usr/bin/env python3
# File: data_collector/src/data_collector/collector_node.py

import os
from datetime import datetime

import cv2
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
from ament_index_python.packages import get_package_share_directory

class ImageCollectorNode(Node):
    def __init__(self):
        super().__init__('image_collector')
        self.bridge = CvBridge()

        # 1) 패키지 share/data 폴더 경로
        pkg_share = get_package_share_directory('data_collector')
        base_dir = os.path.join(pkg_share, 'data_labeling')

        # 2) 날짜 기반 서브폴더 생성
        now = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.out_dir = os.path.join(base_dir, now)
        os.makedirs(self.out_dir, exist_ok=True)

        self.get_logger().info(f"Saving images to: {self.out_dir}")

        # 3) 카메라 이미지 토픽만 구독
        #    (필요에 따라 '/camera/image_raw' 로 변경)
        self.create_subscription(
            Image,
            '/camera/image_raw',
            self.image_cb,
            10
        )

        self.counter = 0

    def image_cb(self, msg: Image):
        # ROS Image → OpenCV BGR
        cv_img = self.bridge.imgmsg_to_cv2(msg, 'bgr8')

        # 파일명: image_000000.png, image_000001.png, ...
        fname = f"image_{self.counter:06d}.png"
        path = os.path.join(self.out_dir, fname)

        # 디스크에 저장
        cv2.imwrite(path, cv_img)
        self.get_logger().info(f"Saved {fname}")

        self.counter += 1

def main(args=None):
    rclpy.init(args=args)
    node = ImageCollectorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
