#!/usr/bin/env python3
import math
import numpy as np
import cv2
import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
from sensor_msgs.msg import Image
from yolo_msgs.msg import DetectionArray
from cv_bridge import CvBridge

def quaternion_to_yaw(qx, qy, qz, qw):
    return math.atan2(
        2.0 * (qw*qz + qx*qy),
        1.0 - 2.0 * (qy*qy + qz*qz)
    )

class ImageFusionNode(Node):
    def __init__(self):
        super().__init__('image_fusion_node')
        self.bridge     = CvBridge()
        self.odom       = None
        self.detections = []

        self.linear_velocity = 0.0
        self.angular_velocity = 0.0

        self.pub = self.create_publisher(Image, '/fused_image', 30)

        self.create_subscription(Odometry,
                                 '/odom',
                                 self.odom_cb,
                                 30)
        self.create_subscription(DetectionArray,
                                 '/yolo/tracking',
                                 self.detections_cb,
                                 30)

        rate = self.declare_parameter('update_rate', 30.0).value
        self.create_timer(1.0 / rate, self.timer_cb)

    def odom_cb(self, msg: Odometry):
        self.odom = msg
        self.linear_velocity = msg.twist.twist.linear.x
        self.angular_velocity = msg.twist.twist.angular.z

    def detections_cb(self, msg: DetectionArray):
        self.detections = msg.detections

    def timer_cb(self):
        H, W = 240, 320
        img = np.zeros((H, W, 3), dtype=np.uint8)

        scale_x = W / float(self.detections[0].mask.width) if self.detections else 1.0
        scale_y = H / float(self.detections[0].mask.height) if self.detections else 1.0

        for det in self.detections:
            if det.score < 0.5:
                continue
            cls = det.class_name.lower()

            if cls == 'passageway' and det.mask.data:
                pts = np.array([
                    [int(pt.x * scale_x), int(pt.y * scale_y)]
                    for pt in det.mask.data
                ], dtype=np.int32).reshape(-1, 1, 2)
                cv2.fillPoly(img, [pts], (255, 0, 0))
                continue

            cx = det.bbox.center.position.x * scale_x
            cy = det.bbox.center.position.y * scale_y
            w  = det.bbox.size.x * scale_x
            h  = det.bbox.size.y * scale_y
            x0 = int(max(0, cx - w/2))
            y0 = int(max(0, cy - h/2))
            x1 = int(min(W, cx + w/2))
            y1 = int(min(H, cy + h/2))

            if cls == 'person':
                cv2.rectangle(img, (x0, y0), (x1, y1), (0, 255, 0), 2)
            elif cls == 'red pillar':
                cv2.rectangle(img, (x0, y0), (x1, y1), (0, 0, 255), 2)

        # 차량 방향 화살표: 방향은 yaw, 길이는 linear_velocity에 비례
        if self.odom:
            q = self.odom.pose.pose.orientation
            yaw = quaternion_to_yaw(q.x, q.y, q.z, q.w) + math.pi / 2

            arrow_length = int(max(30, min(80, abs(self.linear_velocity) * 50)))  # 속도에 따라 길이 조정 (30~80픽셀)
            start_pt = (W // 2, H - 40)
            end_pt = (
                int(start_pt[0] + arrow_length * math.cos(yaw)),
                int(start_pt[1] - arrow_length * math.sin(yaw))
            )
            cv2.arrowedLine(img, start_pt, end_pt, (255, 0, 255), 2, tipLength=0.3)

        out = self.bridge.cv2_to_imgmsg(img, encoding='bgr8')
        out.header.stamp = self.get_clock().now().to_msg()
        self.pub.publish(out)

    def destroy_node(self):
        self.get_logger().info('Shutting down ImageFusionNode')
        super().destroy_node()

def main(args=None):
    rclpy.init(args=args)
    node = ImageFusionNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
