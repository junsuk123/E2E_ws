from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        Node(
            package='data_collector',
            executable='collector_node',
            name='data_collector',
            output='screen',        ),
    ])
