import math
import rclpy
import torch
import numpy as np
from rclpy.node import Node
from sensor_msgs.msg import Image
from geometry_msgs.msg import Twist
from cv_bridge import CvBridge
from torchvision.transforms import Compose, Resize, ToTensor
from torchvision.models import resnet18

class InferenceNode(Node):
    def __init__(self):
        super().__init__('resnet_inference')
        self.bridge = CvBridge()
        model_path = self.declare_parameter('model_path', '/tmp/resnet.pth').value
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        # model 로드
        self.model = resnet18(pretrained=False, num_classes=2).to(self.device)
        self.model.load_state_dict(torch.load(model_path, map_location=self.device))
        self.model.eval()
        # transform
        self.tf = Compose([Resize((240,320)), ToTensor()])
        # subscribers & publisher
        self.create_subscription(Image, 'fused_image', self.cb_image, 10)
        self.pub = self.create_publisher(Twist, 'cmd_vel', 10)

    def cb_image(self, msg):
        # 이미지 → 텐서
        cv_img = self.bridge.imgmsg_to_cv2(msg, 'bgr8')
        x = self.tf(cv_img).unsqueeze(0).to(self.device)
        with torch.no_grad():
            out = self.model(x).cpu().numpy()[0]
        # Twist 생성
        t = Twist()
        t.linear.x  = float(out[1])  # vel
        t.angular.z = float(out[0])  # steer
        self.pub.publish(t)

def main(args=None):
    rclpy.init(args=args)
    node = InferenceNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()
