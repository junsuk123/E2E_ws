from launch import LaunchDescription
from launch_ros.actions import Node
from launch.substitutions import Command, PathJoinSubstitution, FindExecutable
from launch_ros.substitutions import FindPackageShare

def generate_launch_description():
    xacro_file = PathJoinSubstitution([
        FindPackageShare("my_robot_description"),
        "urdf",
        "robot_core.xacro"
    ])

    return LaunchDescription([
        Node(
            package="robot_state_publisher",
            executable="robot_state_publisher",
            name="robot_state_publisher",
            output="screen",
            parameters=[{
                "robot_description": Command([
                    FindExecutable(name="xacro"),
                    " ",
                    xacro_file
                ])
            }]
        ),
        Node(
            package="joint_state_publisher_gui",
            executable="joint_state_publisher_gui",
            name="joint_state_publisher_gui",
            output="screen"
        ),
        Node(
            package="rviz2",
            executable="rviz2",
            name="rviz2",
            output="screen"
        )
    ])
