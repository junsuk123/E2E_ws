import os, csv
import numpy as np
import cv2
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from geometry_msgs.msg import Twist
from cv_bridge import CvBridge
from message_filters import Subscriber, TimeSynchronizer

class CollectorNode(Node):
    def __init__(self):
        super().__init__('data_collector')
        self.bridge = CvBridge()
        self.out_dir = self.declare_parameter('out_dir', '/tmp/drive_data').value
        os.makedirs(self.out_dir, exist_ok=True)
        self.csv_path = os.path.join(self.out_dir, 'data.csv')
        # CSV 헤더 작성
        with open(self.csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['timestamp', 'image_file', 'linear_x', 'angular_z'])
        # TimeSynchronizer 설정
        img_sub   = Subscriber(self, Image, 'fused_image')
        cmd_sub   = Subscriber(self, Twist, 'cmd_vel')
        sync = TimeSynchronizer([img_sub, cmd_sub], 10)
        sync.registerCallback(self.cb)

    def cb(self, img_msg, twist_msg):
        # 1) 이미지 획득
        cv_img = self.bridge.imgmsg_to_cv2(img_msg, 'bgr8')
        ts = img_msg.header.stamp.sec + img_msg.header.stamp.nanosec * 1e-9
        fname = f"{ts:.6f}.png"
        path = os.path.join(self.out_dir, fname)
        cv2.imwrite(path, cv_img)
        # 2) CSV 기록
        with open(self.csv_path, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([f"{ts:.6f}", fname,
                             f"{twist_msg.linear.x:.4f}",
                             f"{twist_msg.angular.z:.4f}"])
        self.get_logger().info(f"Saved {fname}  vx={twist_msg.linear.x:.2f}  wz={twist_msg.angular.z:.2f}")

def main(args=None):
    rclpy.init(args=args)
    node = CollectorNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()
