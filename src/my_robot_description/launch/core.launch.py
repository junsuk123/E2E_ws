import os
import xacro
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    pkg_share = get_package_share_directory('my_robot_description')

    # xacro → URDF
    xacro_path = os.path.join(pkg_share, 'urdf', 'robot_core.xacro')
    robot_desc_pkg = xacro.process_file(xacro_path).toxml()

    # Gazebo용으로 경로 치환
    robot_desc_gazebo = robot_desc_pkg.replace(
        'package://my_robot_description', pkg_share
    )

    # Gazebo에 넘길 임시 URDF 저장
    temp_urdf_path = os.path.join(pkg_share, 'temp_spawn_model.urdf')
    with open(temp_urdf_path, 'w') as f:
        f.write(robot_desc_gazebo)

    # Gazebo world 파일 경로
    world_path = os.path.join(pkg_share, 'worlds', 'AI_Center3.world')

    return LaunchDescription([
        # Pose 인자
        DeclareLaunchArgument('x_pose', default_value='0.0'),
        DeclareLaunchArgument('y_pose', default_value='-1.5'),
        DeclareLaunchArgument('z_pose', default_value='0.0'),

        # Gazebo 실행 (world + plugin 포함)
        ExecuteProcess(
            cmd=[
                'gazebo', '--verbose',
                world_path,
                '-s', 'libgazebo_ros_factory.so'
            ],
            output='screen'
        ),

        # RViz용 robot_state_publisher
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            name='robot_state_publisher',
            output='screen',
            parameters=[{'robot_description': robot_desc_pkg}]
        ),

        # joint_state_publisher_gui
        Node(
            package='joint_state_publisher_gui',
            executable='joint_state_publisher_gui',
            name='joint_state_publisher_gui',
            output='screen'
        ),

        # RViz
        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            output='screen'
        ),

        # spawn_entity.py 로 URDF 스폰 (Gazebo는 실제 경로만 인식함)
        ExecuteProcess(
            cmd=[
                'ros2', 'run', 'gazebo_ros', 'spawn_entity.py',
                '-entity', 'my_mobile',
                '-file', temp_urdf_path,
                '-x', LaunchConfiguration('x_pose'),
                '-y', LaunchConfiguration('y_pose'),
                '-z', LaunchConfiguration('z_pose')
            ],
            output='screen'
        )
    ])
