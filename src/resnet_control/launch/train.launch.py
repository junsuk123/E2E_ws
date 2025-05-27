from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        Node(
            package='resnet_control',
            executable='train_node',
            name='resnet_train',
            output='screen',
            parameters=[
                # data_dir, model_path 생략 시 기본값 사용
                {'epochs': 40},
                {'batch_size': 8},
                {'learning_rate': 1e-3},
            ],
        ),
    ])
