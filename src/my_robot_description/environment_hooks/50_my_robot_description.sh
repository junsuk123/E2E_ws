#!/usr/bin/env sh
# 이 파일은 colcon install 시
# install/<prefix>/share/my_robot_description/ament_cmake/environment_hooks/ 에 복사됩니다.

# 모델 디렉토리 경로
MY_MODEL_PATH="${AMENT_PREFIX_PATH}/share/my_robot_description/models"

# GAZEBO_MODEL_PATH 뒤에 추가
if [ -z "$GAZEBO_MODEL_PATH" ]; then
  export GAZEBO_MODEL_PATH="$MY_MODEL_PATH"
else
  export GAZEBO_MODEL_PATH="$GAZEBO_MODEL_PATH:$MY_MODEL_PATH"
fi
