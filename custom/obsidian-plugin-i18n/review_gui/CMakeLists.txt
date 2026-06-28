# review_gui 审核台构建配置
#
# 用法：把整个 obsidian-plugin-i18n/review_gui 目录复制到 EUI-NEO 源码树根目录下，
# 然后在 EUI-NEO 源码根执行构建（见 build_review_gui.bat）。
# 这样能复用 EUI-NEO 已配置好的所有依赖（glfw/freetype/harfbuzz/glad 等）。

cmake_minimum_required(VERSION 3.14)

# 这个文件设计为 add_subdirectory 到 EUI-NEO 的 CMake 树里，
# 单独运行没意义。用 build_review_gui.bat 自动处理。

if(NOT TARGET eui_neo)
    message(FATAL_ERROR
        "review_gui 必须作为 EUI-NEO 源码树的子目录构建。"
        "请用 build_review_gui.bat，它会自动把本目录接入 EUI-NEO 树。")
endif()

add_executable(review_gui
    review_gui.cpp
    # EUI-NEO 的 app main 入口不在 eui_neo.lib 里，必须一起编译
    # 路径相对 EUI-NEO 源码根（本目录通过 add_subdirectory 接入）
    ${CMAKE_SOURCE_DIR}/core/app/glfw_app_main.cpp
)

# 链接 EUI-NEO 静态库 + 它的公开依赖（PUBLIC 会自动传递）
target_link_libraries(review_gui PRIVATE eui_neo)

# Windows：调试期保留控制台（看 stderr 日志），稳定后改 /SUBSYSTEM:WINDOWS
if(WIN32)
    target_link_options(review_gui PRIVATE
        /OPT:REF
        /OPT:ICF
    )
endif()

# 用 EUI-NEO 的窗口后端定义（glfw）
target_compile_definitions(review_gui PRIVATE
    EUI_WINDOW_BACKEND_GLFW=1
    EUI_RENDER_BACKEND_OPENGL=1
)
