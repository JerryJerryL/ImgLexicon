# ImgLexicon (Case Manager)

ImgLexicon 是一款面向本地图像资料管理与全文检索的工具，旨在解决大量本地图像（如病历、合同、笔记截图等）无法快速搜索的问题。

## 项目核心功能

1. **图像数据管理**：支持指定目录下的图像文件批量导入，并建立本地案例管理索引。
2. **轻量化本地 OCR**：集成高性能推理引擎，自动提取图像文本信息。相比传统框架，显著降低了运行库依赖体积。
3. **关键词全文搜索**：支持通过关键词实时检索图像内容，精准定位目标图像物理路径。
4. **实时状态监测**：内置日志查看模块，实时监控后台识别队列进度。

## 安装与运行

本项目的预编译运行包已发布。若您无需修改源码，建议直接下载：

👉 [**下载 ImgLexicon v1.0.0 完整运行包**](https://github.com/JerryJerryL/ImgLexicon/releases/latest)

1. 下载 ZIP 压缩包并解压。
2. 在解压后的文件夹内双击 `ocr_case_manager.exe` 启动主程序。

## 技术致谢 (Credits)

本项目在 OCR 推理能力的开发过程中，深度参考并采用了以下开源项目：

* **[OnnxOCR](https://github.com/jingsongliujing/OnnxOCR)** (Author: jingsongliujing)：本项目核心 OCR 推理逻辑基于该项目提供的 ONNX 封装方案，极大地优化了部署效率与运行速度。
* **[PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR)**：感谢百度 PaddleOCR 团队提供的中英文通用 OCR 预训练模型。

## 项目贡献者 (Contributors)

* [**Yuchen Li**](https://github.com/JerryJerryL) (@JerryJerryL)：负责主程序逻辑开发、ONNX 模块集成及项目打包。
* [**Haoyuan Chen**](https://github.com/ChenHY532) (@ChenHY532)：感谢在环境配置及代码调试过程中提供的帮助。

## 开源协议

本项目代码部分遵循 MIT 协议。
