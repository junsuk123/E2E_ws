import os
import rclpy
import torch
import torchvision.transforms as T
import torchvision.datasets as D
from torch import nn, optim
from torchvision.models import resnet18
from std_msgs.msg import Float32
from rclpy.node import Node

class TrainNode(Node):
    def __init__(self):
        super().__init__('resnet_train')
        # ROS2 Publisher (loss/accuracy/lr)
        self.loss_pub = self.create_publisher(Float32, 'training/loss', 10)
        self.acc_pub  = self.create_publisher(Float32, 'training/accuracy', 10)
        self.lr_pub   = self.create_publisher(Float32, 'training/lr', 10)
        # 파라미터
        data_dir = self.declare_parameter('data_dir', '/tmp/drive_data').value
        epochs   = self.declare_parameter('epochs', 10).value
        batch    = self.declare_parameter('batch_size', 32).value
        lr_init  = self.declare_parameter('learning_rate', 1e-3).value

        # Dataset & Dataloader
        transform = T.Compose([T.Resize((240,320)), T.ToTensor()])
        dataset   = D.ImageFolder(data_dir, transform=transform)  # CSV parsing code 추가 필요
        loader    = torch.utils.data.DataLoader(dataset, batch_size=batch, shuffle=True)

        # Model, Loss, Optimizer
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model  = resnet18(pretrained=False, num_classes=2).to(self.device)
        self.criterion = nn.MSELoss()
        self.optimizer = optim.Adam(self.model.parameters(), lr=lr_init)
        self.scheduler = optim.lr_scheduler.StepLR(self.optimizer, step_size=5, gamma=0.5)

        # 학습 시작
        for epoch in range(1, epochs+1):
            self.train_one_epoch(loader, epoch)
            self.scheduler.step()

    def train_one_epoch(self, loader, epoch):
        self.model.train()
        total_loss, total_acc = 0.0, 0.0
        for imgs, labels in loader:
            imgs, labels = imgs.to(self.device), labels.to(self.device)  # labels: [steer, vel]
            outputs = self.model(imgs)
            loss = self.criterion(outputs, labels)
            self.optimizer.zero_grad()
            loss.backward()
            self.optimizer.step()

            total_loss += loss.item()
            # accuracy 계산 (예: ±0.1 이내면 correct)
            correct = (torch.abs(outputs - labels) < 0.1).all(dim=1).float().sum().item()
            total_acc += correct / imgs.size(0)

        avg_loss = total_loss / len(loader)
        avg_acc  = total_acc  / len(loader)
        lr       = self.scheduler.get_last_lr()[0]
        # ROS2 퍼블리시
        self.loss_pub.publish(Float32(data=avg_loss))
        self.acc_pub.publish(Float32(data=avg_acc))
        self.lr_pub.publish(Float32(data=lr))
        self.get_logger().info(f"[Epoch {epoch}] loss={avg_loss:.4f} acc={avg_acc:.3f} lr={lr:.5f}")

def main(args=None):
    rclpy.init(args=args)
    node = TrainNode()
    # 학습이 끝나면 spin 유지 (필요 시)
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()
