# ImgLexicon

ImgLexicon 是一款基于 OCR 技术的本地图像案例管理与全文检索工具。

## 项目背景
在处理大量含有文字信息的本地图像（如病历、实验笔记、截图等）时，往往难以通过关键词定位。本项目通过集成轻量化的 OCR 引擎，实现了对本地图像内容的自动化提取与高效检索。

## 快速开始 (下载运行)
如果你不是开发者，只需点击下方的 **Releases** 链接下载编译好的运行包：

[**下载 ImgLexicon v1.0.0 完整版**](https://github.com/JerryJerryL/ImgLexicon/releases/latest)

1. 下载 ZIP 压缩包并解压。
2. 双击 `ocr_case_manager.exe` 即可运行。

## 技术栈
- **核心逻辑**: Python 3.x
- **OCR 推理**: ONNXRuntime (基于 PaddleOCR 模型转换)
- **GUI 界面**: Tkinter / PySide (根据你的实际情况写)

## 使用说明
1. **导入案例**：选择包含图片的文件夹，系统将自动进行 OCR 识别。
2. **关键词搜索**：在搜索框输入文字，即可实时过滤出包含该内容的图片。
3. **日志查看**：通过内置的 Log Viewer 监控后台识别进度。
