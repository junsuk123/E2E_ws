#!/usr/bin/env python3
import os
import csv
from datetime import datetime

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from torchvision.models import resnet18
from PIL import Image as PILImage
from ament_index_python.packages import get_package_share_directory

class DriveDataset(Dataset):
    def __init__(self, data_dir, transform=None):
        self.data_dir = data_dir
        self.transform = transform
        csv_path = os.path.join(self.data_dir, 'data.csv')
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            self.rows = [row for row in reader]

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, idx):
        row = self.rows[idx]
        img_path = os.path.join(self.data_dir, row['image_file'])
        image = PILImage.open(img_path).convert('RGB')
        if self.transform:
            image = self.transform(image)
        steer = float(row['angular_z'])
        vel   = float(row['linear_x'])
        return image, torch.tensor([steer, vel], dtype=torch.float32)

class TrainNode(Node):
    def __init__(self):
        super().__init__('resnet_train')

        # 1) 가장 최근에 저장된 data_collector 데이터 폴더 찾기
        dc_share = get_package_share_directory('data_collector')
        data_base = os.path.join(dc_share, 'data')
        subdirs = sorted([
            d for d in os.listdir(data_base)
            if os.path.isdir(os.path.join(data_base, d))
        ])
        default_data_dir = os.path.join(data_base, subdirs[-1]) if subdirs else data_base
        self.data_dir = self.declare_parameter('data_dir', default_data_dir).value

        # 2) 모델 저장 경로: 패키지 src/resnet_control/models/<timestamp>.pth
        pkg_root   = os.path.dirname(os.path.dirname(__file__))
        model_base = os.path.join(pkg_root, 'models')
        os.makedirs(model_base, exist_ok=True)
        now_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        default_model_path = os.path.join(model_base, f'resnet_{now_str}.pth')
        self.model_path = self.declare_parameter('model_path', default_model_path).value

        # 3) 하이퍼파라미터
        epochs     = self.declare_parameter('epochs', 10).value
        batch_size = self.declare_parameter('batch_size', 32).value
        lr         = self.declare_parameter('learning_rate', 1e-3).value

        # 4) Dataset & DataLoader
        transform = transforms.Compose([
            transforms.Resize((240, 320)),
            transforms.ToTensor()
        ])
        dataset = DriveDataset(self.data_dir, transform)
        loader  = DataLoader(dataset, batch_size=batch_size, shuffle=True)

        # 5) Model / Loss / Optimizer / Scheduler
        self.device    = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model     = resnet18(weights=None, num_classes=2).to(self.device)
        self.criterion = nn.MSELoss()
        self.optimizer = optim.Adam(self.model.parameters(), lr=lr)
        self.scheduler = optim.lr_scheduler.StepLR(self.optimizer, step_size=5, gamma=0.5)

        # 6) ROS2 퍼블리셔 (rqt_plot 등에서 시각화)
        self.loss_pub = self.create_publisher(Float32, 'training/loss', 10)
        self.acc_pub  = self.create_publisher(Float32, 'training/accuracy', 10)
        self.lr_pub   = self.create_publisher(Float32, 'training/lr', 10)

        # 7) Training Loop with checkpoint on interrupt
        try:
            for epoch in range(1, epochs + 1):
                self.train_one_epoch(loader, epoch)
                self.scheduler.step()
            # 정상 완료 시 최종 모델 저장
            torch.save(self.model.state_dict(), self.model_path)
            self.get_logger().info(f"Saved final model to: {self.model_path}")
        except KeyboardInterrupt:
            # 중단 시에도 중간 모델 저장
            tmp_path = self.model_path.replace('.pth', '_interrupted.pth')
            torch.save(self.model.state_dict(), tmp_path)
            self.get_logger().info(f"Training interrupted—saved intermediate model: {tmp_path}")
        finally:
            rclpy.shutdown()

    def train_one_epoch(self, loader, epoch):
        self.model.train()
        total_loss = 0.0
        total_correct = 0
        total_samples = 0
        tol = 0.1

        for imgs, labels in loader:
            imgs, labels = imgs.to(self.device), labels.to(self.device)
            outputs = self.model(imgs)
            loss = self.criterion(outputs, labels)

            self.optimizer.zero_grad()
            loss.backward()
            self.optimizer.step()

            total_loss += loss.item() * imgs.size(0)
            correct = ((torch.abs(outputs - labels) < tol).all(dim=1)).sum().item()
            total_correct += correct
            total_samples += imgs.size(0)

        avg_loss = total_loss / total_samples
        avg_acc  = total_correct / total_samples
        lr_now   = self.scheduler.get_last_lr()[0]

        # ROS2 퍼블리시
        self.loss_pub.publish(Float32(data=avg_loss))
        self.acc_pub.publish(Float32(data=avg_acc))
        self.lr_pub.publish(Float32(data=lr_now))
        self.get_logger().info(
            f"Epoch {epoch}: loss={avg_loss:.4f}, acc={avg_acc:.4f}, lr={lr_now:.6f}"
        )

def main(args=None):
    rclpy.init(args=args)
    node = TrainNode()
    # 노드는 __init__에서 학습을 마치거나 중단 시 shutdown 됩니다
    # 그 이후 spin은 불필요하나, 안전히 대기
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if rclpy.ok():
            node.destroy_node()
            rclpy.shutdown()

if __name__ == '__main__':
    main()
