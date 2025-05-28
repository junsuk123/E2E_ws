from setuptools import setup
from glob import glob
import os

package_name = "yolo_ros"

setup(
    name=package_name,
    version="0.0.0",
    packages=[package_name],
    data_files=[
        # ament resource index
        ('share/ament_index/resource_index/packages',
         ['resource/' + package_name]),
        # package.xml
        ('share/' + package_name, ['package.xml']),
        # launch/ 아래 .launch.py 파일들
        (os.path.join('share', package_name, 'launch'),
         glob(os.path.join('..', 'yolo_bringup', 'launch', '*.launch.py'))),
        # models 폴더 (여기에 .pt 파일을 위치시키세요)
        (os.path.join('share', package_name, 'models'),
         glob(os.path.join('models', '*'))),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Miguel Ángel González Santamarta",
    maintainer_email="mgons@unileon.es",
    description="YOLO for ROS 2",
    license="GPL-3",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "yolo_node = yolo_ros.yolo_node:main",
            "debug_node = yolo_ros.debug_node:main",
            "tracking_node = yolo_ros.tracking_node:main",
            "detect_3d_node = yolo_ros.detect_3d_node:main",
        ],
    },
)
