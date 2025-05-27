from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        Node(
            package='resnet_control',
            executable='inference_node',
            name='resnet_inference',
            output='screen',
            parameters=[{'model_path': '/tmp/resnet.pth'}],
        ),
    ])
