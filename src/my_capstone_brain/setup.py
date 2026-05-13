from setuptools import setup
import os
from glob import glob

package_name = 'my_capstone_brain'

setup(
    name=package_name,
    version='0.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'worlds'), glob('worlds/*.sdf')),
        # THIS IS THE NEW LINE
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')), 
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='mos',
    maintainer_email='mos@todo.todo',
    description='Brain logic for Autonomous Factory Line',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'spawner_node = my_capstone_brain.spawner_node:main',
            'conveyor_node = my_capstone_brain.conveyor_node:main',
            'ik_teleop_node = my_capstone_brain.ik_teleop_node:main',
            'fk_teleop_node = my_capstone_brain.fk_teleop_node:main', # <-- NEW LINE
            'vision_node = my_capstone_brain.vision_node:main',
        ],
    },
)