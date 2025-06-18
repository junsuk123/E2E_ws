cmake_minimum_required(VERSION 3.8)
project(my_robot_description)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# find dependencies
find_package(ament_cmake REQUIRED)

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  set(ament_cmake_copyright_FOUND TRUE)
  set(ament_cmake_cpplint_FOUND TRUE)
  ament_lint_auto_find_test_dependencies()
endif()

# ✅ 로컬 리소스 폴더들 설치
install(
  DIRECTORY launch urdf models worlds environment_hooks
  DESTINATION share/${PROJECT_NAME}
)
# 2) env hook 파일 설치
install(FILES
  environment_hooks/50_my_robot_description.sh
  DESTINATION share/${PROJECT_NAME}/
)
ament_package()
