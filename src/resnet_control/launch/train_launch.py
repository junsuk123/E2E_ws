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
              {'data_dir': '/tmp/drive_data'},
              {'epochs': 20},
              {'batch_size': 16},
              {'learning_rate': 1e-4},
            ],
        ),
    ])
