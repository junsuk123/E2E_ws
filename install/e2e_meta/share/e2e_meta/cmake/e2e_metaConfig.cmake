# generated from ament/cmake/core/templates/nameConfig.cmake.in

# prevent multiple inclusion
if(_e2e_meta_CONFIG_INCLUDED)
  # ensure to keep the found flag the same
  if(NOT DEFINED e2e_meta_FOUND)
    # explicitly set it to FALSE, otherwise CMake will set it to TRUE
    set(e2e_meta_FOUND FALSE)
  elseif(NOT e2e_meta_FOUND)
    # use separate condition to avoid uninitialized variable warning
    set(e2e_meta_FOUND FALSE)
  endif()
  return()
endif()
set(_e2e_meta_CONFIG_INCLUDED TRUE)

# output package information
if(NOT e2e_meta_FIND_QUIETLY)
  message(STATUS "Found e2e_meta: 0.0.0 (${e2e_meta_DIR})")
endif()

# warn when using a deprecated package
if(NOT "" STREQUAL "")
  set(_msg "Package 'e2e_meta' is deprecated")
  # append custom deprecation text if available
  if(NOT "" STREQUAL "TRUE")
    set(_msg "${_msg} ()")
  endif()
  # optionally quiet the deprecation message
  if(NOT ${e2e_meta_DEPRECATED_QUIET})
    message(DEPRECATION "${_msg}")
  endif()
endif()

# flag package as ament-based to distinguish it after being find_package()-ed
set(e2e_meta_FOUND_AMENT_PACKAGE TRUE)

# include all config extra files
set(_extras "")
foreach(_extra ${_extras})
  include("${e2e_meta_DIR}/${_extra}")
endforeach()
