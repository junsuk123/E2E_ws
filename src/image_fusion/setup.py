#!/usr/bin/env python3

from setuptools import setup
from glob import glob
import os
package_name = 'image_fusion'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
         ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py'))
    ],
    install_requires=['setuptools', 'opencv-python', 'numpy', 'cv_bridge'],
    zip_safe=True,
    maintainer='kimjunsuk',
    maintainer_email='bob4587@naver.com',
    description='Fuse vehicle state and detections into a single image',
    license='MIT',
    entry_points={
        'console_scripts': [
            'image_fusion_node = image_fusion.image_fusion_node:main',
        ],
    },
)
