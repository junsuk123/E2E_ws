# launch/image_fusion_launch.py
from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        Node(
            package='image_fusion',
            # module path 를 executable 로 지정
            executable='image_fusion_node',
            output='screen'
        ),
    ])
