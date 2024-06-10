cmake_minimum_required(VERSION 3.12)

set(_change_MSVC_flags FALSE)
if(WIN32)
  if(CMAKE_VERSION VERSION_LESS 3.15.0)
    set(_change_MSVC_flags TRUE)
  else()
    # Set MSVC runtime to MultiThreaded (/MT)
    cmake_policy(SET CMP0091 NEW)
    set(CMAKE_MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>DLL")
  endif()
endif()

project(brms VERSION 0.1 LANGUAGES CXX)

set(CMAKE_INCLUDE_CURRENT_DIR ON)

set(CMAKE_AUTOUIC ON)
set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTORCC ON)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

if(APPLE)
list(APPEND CMAKE_PREFIX_PATH "/Users/adriangao/Qt/6.7.1/macos/lib/cmake")
set(QuantLib "QuantLib")
endif()

find_package(QT NAMES Qt6 Qt5 REQUIRED COMPONENTS Widgets Charts)
find_package(Qt${QT_VERSION_MAJOR} REQUIRED COMPONENTS Widgets Charts)

set(PROJECT_SOURCES
        src/main.cpp
        src/mainwindow.cpp
        include/brms/mainwindow.h
        src/mainwindow.ui
)

# add_compile_definitions(QL_USE_STD_SHARED_PTR)
set(QUANTLIB_INCLUDE_DIR "${CMAKE_SOURCE_DIR}/include/ql")
set(QUANTLIB_LIBRARY_DIR "${CMAKE_SOURCE_DIR}/lib")
include_directories(${QUANTLIB_INCLUDE_DIR})
link_directories(${QUANTLIB_LIBRARY_DIR})


set(Boost_USE_STATIC_LIBS ON)  # Link with static libraries
set(Boost_USE_MULTITHREADED ON)
set(Boost_USE_STATIC_RUNTIME OFF)
find_package(Boost REQUIRED)

if (Boost_FOUND)
    include_directories(${Boost_INCLUDE_DIRS})
endif()

if(${QT_VERSION} VERSION_LESS 6.1.0)
  set(BUNDLE_ID_OPTION MACOSX_BUNDLE_GUI_IDENTIFIER com.mingze-gao.brms)
endif()

if(${QT_VERSION_MAJOR} GREATER_EQUAL 6)
    qt_add_executable(brms
        MANUAL_FINALIZATION
        ${PROJECT_SOURCES}
        ${EXTERNAL_LIB}
        include/brms/yieldcurvewindow.h src/yieldcurvewindow.cpp src/yieldcurvewindow.ui
        include/brms/yieldcurvedatamodel.h src/yieldcurvedatamodel.cpp
        include/brms/treeitem.h src/treeitem.cpp
        include/brms/treemodel.h src/treemodel.cpp
        include/brms/bank.h src/bank.cpp
        include/brms/instruments.h src/instruments.cpp
        include/brms/utils.h
        include/brms/bankassets.h src/bankassets.cpp
        include/brms/bankliabilities.h src/bankliabilities.cpp
        include/brms/bankequity.h src/bankequity.cpp
        include/brms/managementwindow.h src/managementwindow.cpp src/managementwindow.ui
    )
endif()

include(GNUInstallDirs)
install(TARGETS brms
    BUNDLE DESTINATION .
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
)

set_target_properties(brms PROPERTIES
    ${BUNDLE_ID_OPTION}
    MACOSX_BUNDLE_BUNDLE_VERSION ${PROJECT_VERSION}
    MACOSX_BUNDLE_SHORT_VERSION_STRING ${PROJECT_VERSION_MAJOR}.${PROJECT_VERSION_MINOR}
    MACOSX_BUNDLE TRUE
    WIN32_EXECUTABLE TRUE
)

target_link_libraries(brms PRIVATE ${QuantLib} ${Boost_LIBRARIES} Qt${QT_VERSION_MAJOR}::Widgets Qt${QT_VERSION_MAJOR}::Charts)
target_include_directories(brms PRIVATE "${CMAKE_CURRENT_LIST_DIR}/include")

# Resources:
set(brms_resource_files
    "resources/par_yields.csv"
    "resources/treasury_futures.html"
)

qt_add_resources(brms "brms"
    PREFIX
        "/"
    FILES
        ${brms_resource_files}
)

if(QT_VERSION_MAJOR EQUAL 6)
    qt_finalize_executable(brms)
endif()
