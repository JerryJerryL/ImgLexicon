"""
OCR案件管理器
=================

本脚本实现了一个图形化应用程序，用于组织和搜索从图像文档中提取的文本。
它允许用户导入按子文件夹组织的图像目录（例如"车辆保单"、"警方笔录"等），
对图像运行光学字符识别（OCR），将结果整理成单个文本文档，
并执行带可选过滤器的关键词搜索。聚合的文本文档可以导出为纯文本文件。
搜索结果中的匹配项可以打开以显示原始图像和识别的文本。

依赖项
------------

程序需要以下Python包：

* **Pillow** — 用于图像加载和显示。Pillow已经包含在许多Python发行版中。
  如果缺少，可以使用 `pip install pillow` 安装。
* **OCR引擎** — `paddleocr` 是基于PaddlePaddle的深度学习OCR库。
  安装PaddlePaddle后，可以使用 `pip install paddleocr` 安装。
  官方快速入门指南演示了如何实例化 `PaddleOCR` 对象并调用其
  `predict` 方法以获得识别的文本。

如果应用程序运行时 `paddleocr` 不可用，用户将被告知OCR功能已禁用，
并将插入占位符文本而不是真实的OCR结果。

使用方法
-----

使用Python 3运行脚本：

    python ocr_case_manager.py

主窗口由以下几个部分组成：

1. 案件控制：输入案件名称并点击**导入**，选择包含该案件图像的目录，
   其直接子文件夹包含图像。导入后，程序将遍历文件夹，对每个图像文件
   执行OCR并整理提取的文本。进度条告知用户处理状态。
2. 搜索控制：搜索词的关键词输入和可选的过滤器输入。过滤器将搜索
   范围缩小到包含给定字符串的图像文件名或文件夹名。点击**搜索**
   在结果列表中显示匹配结果。
3. 结果列表：每个匹配显示一个条目。双击结果会打开一个窗口，
   显示完整的识别文本和相应的图像。
4. 导出按钮：将聚合的案件文本写入 `.txt` 文件。

打包
---------

要将应用程序分发为独立的可执行文件，可以使用PyInstaller。
首先使用 `pip install pyinstaller` 安装它。然后在包含此脚本的
目录中运行以下命令：

    pyinstaller --onefile -w ocr_case_manager.py

`--onefile` 选项将所有依赖项捆绑到单个可执行文件中，
`-w` 防止在运行GUI程序时出现控制台窗口。生成的可执行文件
将放置在 `dist` 目录中。
"""

import os
import threading
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from onnxocr.onnx_paddleocr import ONNXPaddleOcr as PaddleOCR
try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
except ImportError:
    # Fallback if tkinter is not available (e.g. in some minimal
    # environments). The application cannot run without a GUI, so
    # raise an informative error.
    raise ImportError(
        "Tkinter is not available in this Python environment. Please "
        "install the 'tk' package or use a Python distribution that "
        "includes Tkinter to run this application."
    )

try:
    from PIL import Image, ImageTk, ImageOps
except ImportError:
    raise ImportError(
        "Pillow (PIL) is not available in this Python environment. "
        "Please install it with 'pip install pillow' to run this application."
    )

# Check if PaddleOCR is available
def _check_paddle_available() -> bool:
    """检查PaddleOCR是否可用。"""
    try:
        import paddleocr
        
        # 获取日志系统（如果可用）
        log_viewer = None
        try:
            from log_viewer import get_log_viewer
            log_viewer = get_log_viewer()
        except:
            pass
        
        if log_viewer:
            log_viewer.log_info(f"✅ PaddleOCR 模块路径：{paddleocr.__file__}")
            log_viewer.log_info(f"✅ PaddleOCR 版本：{paddleocr.__version__ if hasattr(paddleocr, '__version__') else '未知'}")
        
        # 检查关键文件是否存在
        import os
        paddleocr_dir = os.path.dirname(paddleocr.__file__)
        if log_viewer:
            log_viewer.log_info(f"📁 PaddleOCR 目录：{paddleocr_dir}")
        
        # 检查字典文件路径
        dict_path = os.path.join(paddleocr_dir, 'utils', 'ppocr_keys_v1.txt')
        if os.path.exists(dict_path):
            if log_viewer:
                log_viewer.log_info(f"✅ 字典文件存在：{dict_path}")
        else:
            if log_viewer:
                log_viewer.log_info(f"❌ 字典文件不存在：{dict_path}")
            # 尝试其他可能的路径
            alt_paths = [
                os.path.join(paddleocr_dir, 'ppocr_keys_v1.txt'),
                os.path.join(paddleocr_dir, 'utils', 'ppocr_keys_v1.txt'),
                os.path.join(paddleocr_dir, '..', 'utils', 'ppocr_keys_v1.txt'),
                os.path.join(paddleocr_dir, '..', 'ppocr_keys_v1.txt'),
                os.path.join(paddleocr_dir, '..', '..', 'utils', 'ppocr_keys_v1.txt')
            ]
            dict_found = False
            for alt_path in alt_paths:
                if os.path.exists(alt_path):
                    if log_viewer:
                        log_viewer.log_info(f"✅ 找到字典文件：{alt_path}")
                    dict_found = True
                    break
            if not dict_found:
                if log_viewer:
                    log_viewer.log_info("❌ 未找到字典文件，但PaddleOCR会自动处理")
        
        return True
    except ImportError as e:
        # 获取日志系统（如果可用）
        try:
            from log_viewer import get_log_viewer
            log_viewer = get_log_viewer()
            if log_viewer:
                log_viewer.log_info(f"❌ PaddleOCR 导入失败：{e}")
        except:
            pass
        return False
    except Exception as e:
        # 获取日志系统（如果可用）
        try:
            from log_viewer import get_log_viewer
            log_viewer = get_log_viewer()
            if log_viewer:
                log_viewer.log_info(f"❌ PaddleOCR 检查失败：{e}")
        except:
            pass
        return False

# OCR可用性的全局变量
_paddle_available = True #_check_paddle_available()

# 如果可用，全局导入PaddleOCR
'''if _paddle_available:
    try:
        from paddleocr import PaddleOCR
    except ImportError:
        PaddleOCR = None
else:
    PaddleOCR = None

import paddle
paddle.set_device('cpu')'''

# ==== PATCH START: Speed Tune Config (集中开关) ====
# 打开/关闭本次性能改造
ENABLE_SPEED_TUNE = True

# 小批量的张数；设为 1 等于关闭 batch
BATCH_SIZE = 1

# 统一的长边缩放上限（也作为 det_limit_side_len 使用，便于保持一致）
# A4整页文字建议 448~512；照片/票据可用 384 以换速度
DET_LIMIT_SIDE_LEN = 720  # 保持1024以确保识别质量

# Paddle 在 CPU 的算子线程数（不是 Python 线程）
CPU_THREADS_FOR_PADDLE = 2  # 增加到4线程

# 文件系统编码设置（确保中文文件名支持）
import sys
import locale
# 设置默认编码为UTF-8
if hasattr(sys, 'setdefaultencoding'):
    sys.setdefaultencoding('utf-8')
# 设置文件系统编码
os.environ['PYTHONIOENCODING'] = 'utf-8'

# 可选：限制底层数学库的并行度，避免把整机吃满（不想限制就注释掉）
import os
os.environ.setdefault("OMP_NUM_THREADS", "4")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "4")
os.environ.setdefault("MKL_NUM_THREADS", "4")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "4")
# ==== PATCH END ====


@dataclass
class Record:
    """
    表示从图像文件中提取的单个OCR记录。

    属性
    ----------
    folder: str
        图像的直接父文件夹名称（文档类型）。
    filename: str
        图像文件的基本名称。
    filepath: str
        图像文件在磁盘上的完整路径。存储完整路径
        确保当用户双击搜索结果时可以重新打开原始图像。
    text: str
        从图像中提取的OCR输出文本。如果OCR不可用，
        这可能包含解释情况的占位符。
    """

    folder: str
    filename: str
    filepath: str
    text: str


class CaseManagerApp:
    def __init__(self, master: tk.Tk) -> None:
        self.master = master
        self.master.title("OCR案件管理器")
        self.master.geometry("1000x700")
        
        self.records: List[Record] = []
        self.aggregated_text = ""
        self.progress_var = tk.DoubleVar()
        self.ocr_error_shown = False
        self.log_window = None  # 添加这行
        
        # Initialize log viewer
        try:
            from log_viewer import get_log_viewer
            self.log_viewer = get_log_viewer()
            if self.log_viewer:
                self.log_viewer.log_info("🔧 开始初始化CaseManagerApp...")
                self.log_viewer.log_info("📋 初始化变量...")
                self.log_viewer.log_info(f"📊 OCR状态: PaddleOCR={_paddle_available}, Tesseract={False}")
                self.log_viewer.log_info("📝 初始化日志系统...")
                self.log_viewer.log_info("✅ 日志系统初始化成功")
        except Exception as e:
            if self.log_viewer:
                self.log_viewer.log_info(f"❌ 日志系统初始化失败: {e}")
            self.log_viewer = None
        
        if self.log_viewer:
            self.log_viewer.log_info("🖥️ 构建用户界面...")
        self._build_ui()
        
        if self.log_viewer:
            self.log_viewer.log_info("🤖 初始化PaddleOCR...")
        # 如果PaddleOCR可用，创建单个模型实例以供重复使用。
        # 否则保持为None。创建模型相对昂贵，所以我们避免在每次调用时构造它。
        if _paddle_available:
            # 使用合理的默认值实例化OCR模型。我们
            # 禁用文档方向、去扭曲和文本行方向分类以提高性能，
            # 如PaddleOCR快速入门指南所示。
            try:
                if self.log_viewer:
                    self.log_viewer.log_paddleocr_init_start()
                    self.log_viewer.log_info("🔧 开始创建PaddleOCR实例...")
                    self.log_viewer.log_info(f"📋 PaddleOCR参数：lang=ch, det_db_box_thresh=0.5, det_db_unclip_ratio=2.0, det_limit_side_len={DET_LIMIT_SIDE_LEN}, use_angle_cls=True, cpu_threads={CPU_THREADS_FOR_PADDLE}")
                
                # 使用线程包装PaddleOCR初始化，防止卡住
                import threading
                init_success = [False]
                init_error = [None]
                
                def init_ocr():
                    try:
                        self.paddle_ocr = PaddleOCR(
                            #det_model_dir='./models/PP-OCRv5_server_det',
                            #rec_model_dir='./models/PP-OCRv5_server_rec',
                            lang='ch',
                            det_db_box_thresh=0.5,
                            det_db_unclip_ratio=2.0,
                            det_limit_side_len=DET_LIMIT_SIDE_LEN,
                            use_angle_cls=True,  # 启用文本方向检测
                            cpu_threads=CPU_THREADS_FOR_PADDLE,
                        )
                        init_success[0] = True
                        if self.log_viewer:
                            self.log_viewer.log_info("✅ PaddleOCR实例创建成功")
                            self.log_viewer.log_info(f"🔍 PaddleOCR实例类型：{type(self.paddle_ocr)}")
                    except Exception as e:
                        init_error[0] = str(e)
                        if self.log_viewer:
                            self.log_viewer.log_paddleocr_init_failed(str(e))
                            self.log_viewer.log_info(f"❌ PaddleOCR初始化失败: {e}")
                
                thread = threading.Thread(target=init_ocr)
                thread.start()
                thread.join(timeout=500)  # 300秒超时
                
                if not init_success[0]:
                    if self.log_viewer:
                        self.log_viewer.log_info("⏰ PaddleOCR 初始化超时或失败")
                    if init_error[0]:
                        if self.log_viewer:
                            self.log_viewer.log_info(f"❌ 初始化错误: {init_error[0]}")
                    self.paddle_ocr = None
                else:
                    if self.log_viewer:
                        self.log_viewer.log_info("✅ PaddleOCR初始化完成")
                
                # 测试PaddleOCR是否正常工作
                if self.paddle_ocr is not None:
                    if self.log_viewer:
                        self.log_viewer.log_paddleocr_test_start()
                    
                    # 创建一个简单的测试图片来验证PaddleOCR
                    import numpy as np
                    test_img = np.ones((100, 100, 3), dtype=np.uint8) * 255  # 白色图片
                    
                    try:
                        # 使用predict()方法（推荐方法）
                        test_result = self.paddle_ocr.ocr(test_img)
                        if self.log_viewer:
                            self.log_viewer.log_paddleocr_init_success()
                        if self.log_viewer:
                            self.log_viewer.log_info("✅ PaddleOCR初始化成功")
                    except Exception as ocr_error:
                        if self.log_viewer:
                            self.log_viewer.log_paddleocr_init_failed(str(ocr_error))
                            self.log_viewer.log_info(f"❌ PaddleOCR测试失败: {ocr_error}")
                        self.paddle_ocr = None
                else:
                    if self.log_viewer:
                        self.log_viewer.log_info("⚠️ PaddleOCR初始化失败，OCR功能将不可用")
                    
            except Exception as e:
                self.paddle_ocr = None
                if self.log_viewer:
                    self.log_viewer.log_paddleocr_init_failed(str(e))
                    self.log_viewer.log_info(f"❌ PaddleOCR初始化异常: {e}")
        else:
            self.paddle_ocr = None
            if self.log_viewer:
                self.log_viewer.log_paddleocr_status(False, "PaddleOCR未安装")
                self.log_viewer.log_info("⚠️ PaddleOCR未安装")
        
        if self.log_viewer:
            self.log_viewer.log_info("🎉 CaseManagerApp初始化完成")

    # ------------------------------------------------------------------
    # 用户界面构建
    #
    def _build_ui(self) -> None:
        # 案件控制框架
        case_frame = ttk.LabelFrame(self.master, text="案件控制")
        case_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(case_frame, text="案件名称:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.case_entry = ttk.Entry(case_frame)
        self.case_entry.grid(row=0, column=1, sticky="we", padx=5, pady=5)
        self.case_entry.insert(0, "未命名")

        import_btn = ttk.Button(case_frame, text="导入", command=self.import_case)
        import_btn.grid(row=0, column=2, padx=5, pady=5)

        export_btn = ttk.Button(case_frame, text="导出", command=self.export_text)
        export_btn.grid(row=0, column=3, padx=5, pady=5)

        # 扩展输入框以填充水平空间
        case_frame.columnconfigure(1, weight=1)

        # 进度条
        self.progress = ttk.Progressbar(case_frame, orient="horizontal", length=200, mode="determinate")
        self.progress.grid(row=1, column=0, columnspan=4, sticky="we", padx=5, pady=5)

        # 搜索框架
        search_frame = ttk.LabelFrame(self.master, text="搜索选项")
        search_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(search_frame, text="关键词:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.keyword_entry = ttk.Entry(search_frame)
        self.keyword_entry.grid(row=0, column=1, sticky="we", padx=5, pady=5)
        search_frame.columnconfigure(1, weight=1)
        # 选择文件夹按钮
        folder_btn = ttk.Button(search_frame, text="选择文件夹", command=self.show_folder_menu)
        folder_btn.grid(row=0, column=2, padx=5, pady=5)
        # 搜索按钮
        search_btn = ttk.Button(search_frame, text="搜索", command=self.perform_search)
        search_btn.grid(row=0, column=3, padx=5, pady=5)
        search_frame.columnconfigure(3, weight=1)
        self.selected_folder = ""  # 保存当前选择的文件夹路径

        # 结果框架
        results_frame = ttk.LabelFrame(self.master, text="搜索结果")
        results_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # 使用Treeview以获得更好的格式：文件夹、文件名和文本片段的列
        columns = ("folder", "filename", "snippet")
        self.results_tree = ttk.Treeview(results_frame, columns=columns, show="headings", height=15)
        self.results_tree.heading("folder", text="文件夹")
        self.results_tree.heading("filename", text="文件名")
        self.results_tree.heading("snippet", text="匹配文本片段")
        self.results_tree.column("folder", width=150, anchor="w")
        self.results_tree.column("filename", width=150, anchor="w")
        self.results_tree.column("snippet", width=400, anchor="w")
        self.results_tree.pack(fill="both", expand=True, side="left")

        # Bind double click on tree items
        self.results_tree.bind("<Double-1>", self.on_result_double_click)

        # Add a scrollbar
        scrollbar = ttk.Scrollbar(results_frame, orient="vertical", command=self.results_tree.yview)
        self.results_tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

        # 日志按钮区域
        from PIL import Image, ImageTk
        log_frame = ttk.Frame(self.master)
        log_frame.place(relx=1.0, rely=0.0, anchor="ne", x=-10, y=10)  # 右上角，边距10px

        # 缩放图标为32x32
        try:
            img = Image.open("imgs/log_logo.png")
            img = img.resize((32, 32), Image.ANTIALIAS)
            self.log_icon = ImageTk.PhotoImage(img)
            log_btn = ttk.Button(log_frame, image=self.log_icon, command=self.show_log_window, width=32)
        except Exception:
            log_btn = ttk.Button(log_frame, text="日志", command=self.show_log_window, width=4)

        log_btn.pack()

        # 鼠标悬停提示
        def on_enter(event):
            self.status_var.set("查看日志")
        def on_leave(event):
            self.status_var.set("")
        log_btn.bind("<Enter>", on_enter)
        log_btn.bind("<Leave>", on_leave)

        # 状态栏显示提示
        self.status_var = tk.StringVar()
        status_bar = ttk.Label(self.master, textvariable=self.status_var, relief="sunken", anchor="w")
        status_bar.pack(side="bottom", fill="x")

    def show_log_window(self):
        if not self.log_window:
            from log_viewer import LogWindow
            self.log_window = LogWindow(self.master, self.log_viewer)
        # 保持与旧版一致：不写任何性能日志
        self.log_window.show()

    # ------------------------------------------------------------------
    # Case import and OCR processing
    #
    def import_case(self) -> None:
        # Let the user choose a directory. The chosen directory should
        # contain subdirectories representing document categories.
        directory = filedialog.askdirectory(title="Select Case Directory")
        if not directory:
            return

        # Reset current state
        self.records.clear()
        self.aggregated_text = ""
        self.case_name = self.case_entry.get().strip() or "Untitled"
        self.progress['value'] = 0

        # 递归保存文件夹结构
        def build_tree(path: str, is_root: bool = True) -> dict:
            tree = {}
            try:
                for entry in os.listdir(path):
                    full_path = os.path.join(path, entry)
                    if os.path.isdir(full_path):
                        tree[entry] = build_tree(full_path, is_root=False)
            except Exception:
                pass
            return {"": tree} if is_root else tree
        self.folder_tree = build_tree(directory)
        print(self.folder_tree)
        # 递归收集所有图片（包括首级菜单）
        def collect_all_images(folder, folder_name):
            paths = []
            try:
                for entry in os.listdir(folder):
                    full_path = os.path.join(folder, entry)
                    if os.path.isdir(full_path):
                        subfolder_name = os.path.join(folder_name, entry) if folder_name else entry
                        paths.extend(collect_all_images(full_path, subfolder_name))
                    elif self._is_image_file(entry):
                        # 首级菜单的图片：folder_name为空字符串
                        paths.append((folder_name, full_path))
                        if self.log_viewer:
                            self.log_viewer.log_info(f"📁 发现图片: {entry} | 文件夹: {folder_name or '首级菜单'}")
            except Exception as e:
                if self.log_viewer:
                    self.log_viewer.log_info(f"⚠️ 扫描文件夹失败: {folder} | 错误: {e}")
            return paths
        folder_paths = collect_all_images(directory, "")

        if not folder_paths:
            messagebox.showinfo("No Images Found", 
                "The selected directory does not contain any images. "
                "Please select a directory that contains image files directly "
                "or in subfolders.")
            return

        # 记录案件导入
        if self.log_viewer:
            self.log_viewer.log_case_import(self.case_name, len(folder_paths))

        # Start OCR in a separate thread to avoid blocking the UI
        threading.Thread(target=self._process_images, args=(folder_paths,), daemon=True).start()

    def _process_images(self, folder_paths: List[Tuple[str, str]]) -> None:
        """两阶段处理：先统一调整尺寸（如需），再逐张识别。进度条按两阶段合计推进。"""
        total = len(folder_paths)
        if total == 0:
            return
        total_steps = total * 2  # 调整尺寸阶段 + OCR阶段

        # 准备临时目录
        temp_dir = "temp_resized_imgs"
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)

        # 第一阶段：统一调整尺寸
        processed_paths: List[Tuple[str, str, str]] = []  # (folder, original_path, path_for_ocr)
        max_size = DET_LIMIT_SIDE_LEN  # 使用统一配置，保持与检测阈值一致
        for idx, (folder, filepath) in enumerate(folder_paths, start=1):
            path_for_ocr = filepath
            try:
                img = Image.open(filepath)
                old_size = img.size
                if max(old_size) > max_size:
                    ratio = max_size / max(old_size)
                    new_size = (int(old_size[0] * ratio), int(old_size[1] * ratio))
                    resized = img.resize(new_size, Image.LANCZOS)
                    import uuid
                    temp_filename = f"resized_{uuid.uuid4().hex[:8]}_{os.path.basename(filepath)}"
                    temp_path = os.path.join(temp_dir, temp_filename)
                    resized.save(temp_path, 'JPEG', quality=40)
                    path_for_ocr = temp_path
                    if self.log_viewer:
                        # 动作事件：调整尺寸
                        self.log_viewer.log_resize_image(filepath, temp_path, old_size, new_size)
                else:
                    new_size = old_size
            except Exception as e:
                # 如果缩放失败，回退到原图
                path_for_ocr = filepath
                new_size = None
                if self.log_viewer:
                    self.log_viewer.log_info(f"⚠️ 调整尺寸失败，使用原图: {os.path.basename(filepath)} | 错误: {e}")
            processed_paths.append((folder, filepath, path_for_ocr))  # 保存原始路径和OCR路径
            # 进度条：调整尺寸阶段推进
            self._update_progress((idx / total_steps) * 100)

        # ==== PATCH START: 第二阶段小批量 ====
        jdx = 0
        batch_buf = []

        def _flush_batch(buf):
            if not buf:
                return
            # 日志
            if self.log_viewer:
                names = [os.path.basename(p[2]) for p in buf]
                self.log_viewer.log_info(f"🧺 批量OCR开始: {len(buf)} 张 -> {', '.join(names)}")
            import time as _t
            _t0 = _t.perf_counter()

            paths_for_ocr = [p[2] for p in buf]
            texts = self._perform_ocr_batch(paths_for_ocr)

            elapsed_ms = (_t.perf_counter() - _t0) * 1000.0
            per_img = elapsed_ms / max(1, len(buf))
            if self.log_viewer:
                self.log_viewer.log_info(f"🧺 批量OCR完成: {len(buf)} 张 | 总用时 {elapsed_ms:.1f}ms | 平均 {per_img:.1f}ms/张")

            # 写入记录、推进进度
            nonlocal jdx
            for (folder, original_path, path_for_ocr), text in zip(buf, texts):
                if self.log_viewer:
                    self.log_viewer.log_ocr_action_done(path_for_ocr, len(text or ""), per_img)
                self.records.append(Record(
                    folder=folder,
                    filename=os.path.basename(original_path),
                    filepath=original_path,
                    text=text or "",
                ))
                jdx += 1
                self._update_progress(((total + jdx) / total_steps) * 100)

        for tpl in processed_paths:
            batch_buf.append(tpl)
            if len(batch_buf) >= (BATCH_SIZE if ENABLE_SPEED_TUNE else 1):
                _flush_batch(batch_buf)
                batch_buf = []
        # 末尾残余
        _flush_batch(batch_buf)
        # ==== PATCH END ====

        # 第二阶段结束后，构建聚合文本
        self._build_aggregated_text()

        # 清理临时目录（遵循偏好，处理完后清理）
        try:
            import shutil
            shutil.rmtree(temp_dir)
        except Exception:
            pass

        # 完成通知
        self._update_progress(100)
        message = "Import completed successfully. You can now search the extracted text."
        self.master.after(0, lambda: messagebox.showinfo("Import Complete", message))

    def _update_progress(self, value: float) -> None:
        # Updates the progress bar from the main thread
        self.master.after(0, lambda: self.progress.config(value=value))

    # ==== PATCH START: 批量OCR辅助 ====
    def _perform_ocr_batch(self, paths):
        """
        批量识别，返回与 paths 等长的文本列表。
        先尝试 batch 接口；如失败自动回退到逐张识别，保证兼容。
        """
        texts = [""] * len(paths)
        if not getattr(self, "paddle_ocr", None):
            return texts

        try:
            # 优先使用 batch 输入（同一模型复用，省初始化/调度开销）
            # 方案A：predict 支持列表（你的版本日志显示可行）
            results = self.paddle_ocr.ocr(paths)
            parsed = []
            for r in results:
                # 统一解析为纯文本；不同版本字段不同，做几层兜底
                t = ""
                try:
                    # 根据日志显示的OCRResult对象结构进行解析
                    if hasattr(r, "texts") and r.texts:
                        t = "\n".join(r.texts)
                    elif hasattr(r, "ocr_text") and callable(r.ocr_text):
                        t = r.ocr_text()
                    elif hasattr(r, "to_dict"):
                        d = r.to_dict()
                        lines = d.get("texts") or d.get("lines") or []
                        t = "\n".join(lines) if isinstance(lines, list) else str(lines)
                    else:
                        # 新增：直接尝试获取文本内容
                        # 根据日志，OCRResult对象有texts属性
                        if hasattr(r, 'texts'):
                            if isinstance(r.texts, list):
                                t = "\n".join([str(line) for line in r.texts if line])
                            else:
                                t = str(r.texts)
                        # 如果还是没有，尝试其他可能的属性
                        elif hasattr(r, 'text'):
                            t = str(r.text)
                        elif hasattr(r, 'content'):
                            t = str(r.content)
                except Exception as e:
                    if self.log_viewer:
                        self.log_viewer.log_info(f"⚠️ 解析OCR结果失败: {type(r)} | 错误: {e}")
                    t = ""
                parsed.append(t)
            # 若全部为空，说明解析没对上，回退到方案B
            if any(p for p in parsed):
                if self.log_viewer:
                    self.log_viewer.log_info(f"✅ 批量OCR解析成功，提取到 {len([p for p in parsed if p])} 个有效文本")
                return parsed

            # 方案B：标准 paddleocr.ocr(batch)（大多数版本可用）
            batch_out = self.paddle_ocr.ocr(paths, det=True, rec=True, cls=False)
            texts = []
            for per_img in batch_out:
                lines = []
                for item in per_img or []:
                    # item: [points, (text, score)] 或类似结构
                    try:
                        txt = item[1][0] if isinstance(item[1], (list, tuple)) else str(item[1])
                        lines.append(txt)
                    except Exception:
                        pass
                texts.append("\n".join(lines))
            return texts

        except Exception:
            # 任一 batch 调用失败则回退逐张，保证稳定
            out = []
            for p in paths:
                out.append(self._perform_ocr(p))
            return out
    # ==== PATCH END ====

    def _safe_filename(self, filename: str) -> str:
        """安全处理文件名，确保中文文件名能够正确保存和读取"""
        try:
            # 尝试使用UTF-8编码
            return filename.encode('utf-8').decode('utf-8')
        except UnicodeError:
            # 如果编码失败，使用ASCII安全名称
            import uuid
            ext = os.path.splitext(filename)[1]
            return f"file_{uuid.uuid4().hex[:8]}{ext}"

    def _perform_ocr(self, image_path: str) -> str:
        """对给定的图像文件运行OCR并返回识别的文本。

        如果OCR引擎或pytesseract不可用，返回信息性占位符消息
        而不是抛出异常。
        """
        temp_file_path = None
        
        try:
            # 基础耗时记录（常规日志）：总开始
            import time as _t
            _total_start = _t.perf_counter()
            # 移除性能统计逻辑，回到原有简单流程
            # 检查文件是否存在
            if not os.path.exists(image_path):
                error_msg = f"Image file not found: {image_path}"
                if self.log_viewer:
                    self.log_viewer.log_file_not_found(image_path)
                return f"[{error_msg}]"
            
            # 尝试打开图片
            try:
                _open_start = _t.perf_counter()
                image = Image.open(image_path)
                # 验证图片是否有效
                image.verify()
                # 重新打开（verify会关闭图片）
                image = Image.open(image_path)
                # 记录打开图片耗时
                if self.log_viewer:
                    _open_ms = (_t.perf_counter() - _open_start) * 1000.0
                    self.log_viewer.log_info(f" 步骤: 打开图片 | 文件: {os.path.basename(image_path)} | 用时: {_open_ms:.1f}ms")
                
                # 记录图片信息
                if self.log_viewer:
                    self.log_viewer.log_image_info(image_path, image.size, image.mode)
                    
            except Exception as e:
                error_msg = f"Error opening/verifying image: {e}"
                if self.log_viewer:
                    self.log_viewer.log_image_open_failed(image_path, str(e))
                return f"[{error_msg}]"

            # 优先使用PaddleOCR（如果可用）
            if self.paddle_ocr is not None:
                try:
                    # 检查PaddleOCR是否正确初始化
                    if self.paddle_ocr is None:
                        error_msg = "PaddleOCR not properly initialized"
                        if self.log_viewer:
                            self.log_viewer.log_paddleocr_not_initialized()
                        return f"[{error_msg}]"
                    
                    # 处理路径编码问题，确保中文路径能被正确读取
                    import pathlib
                    # 使用UTF-8编码处理路径，确保中文正常
                    try:
                        normalized_path = str(pathlib.Path(image_path).resolve())
                    except UnicodeEncodeError:
                        # 如果遇到编码问题，使用原始路径
                        normalized_path = image_path
                    
                    # 检查图片是否有效
                    if image.size[0] == 0 or image.size[1] == 0:
                        if self.log_viewer:
                            self.log_viewer.log_image_zero_dimensions(image_path)
                        raise ValueError("Image has zero dimensions")
                    
                    # 转换图片格式，确保兼容性
                    if image.mode not in ['RGB', 'L']:
                        image = image.convert('RGB')
                        if self.log_viewer:
                            self.log_viewer.log_image_format_conversion(image_path, "RGB")
                    

                    
                    # 预处理计时开始
                    _pre_start = _t.perf_counter()
                    # 如果图片太大，先缩放并保存到临时文件夹
                    max_size = DET_LIMIT_SIDE_LEN  # 使用配置的尺寸限制
                    if max(image.size) > max_size:
                        # 确保临时文件夹存在
                        temp_dir = "temp_resized_imgs"
                        if not os.path.exists(temp_dir):
                            os.makedirs(temp_dir)
                        
                        # 生成临时文件名（支持中文，使用UTF-8编码）
                        import uuid
                        base_name = os.path.basename(image_path)
                        # 使用安全文件名处理，确保中文正常
                        safe_base_name = self._safe_filename(base_name)
                        name_without_ext = os.path.splitext(safe_base_name)[0]
                        ext = os.path.splitext(safe_base_name)[1]
                        # 使用原文件名 + UUID，确保中文正常显示
                        temp_filename = f"resized_{name_without_ext}_{uuid.uuid4().hex[:8]}{ext}"
                        temp_file_path = os.path.join(temp_dir, temp_filename)
                        
                        # 缩放图片
                        ratio = max_size / max(image.size)
                        new_size = (int(image.size[0] * ratio), int(image.size[1] * ratio))
                        resized_image = image.resize(new_size, Image.LANCZOS)
                        
                        # 记录缩放信息
                        if self.log_viewer:
                            self.log_viewer.log_image_resize(image.size, new_size, ratio)
                        
                        # 保存到临时文件夹，使用较低的JPEG质量，进一步减小体积
                        resized_image.save(temp_file_path, 'JPEG', quality=40)
                        normalized_path = temp_file_path
                        
                        # 记录临时文件信息
                        temp_size = os.path.getsize(temp_file_path) / 1024  # KB
                        if self.log_viewer:
                            self.log_viewer.log_temp_file_created(os.path.basename(temp_file_path), temp_size)
                        
                        # 取消二次缩放以减少额外的计算与IO
                    
                    # 记录预处理耗时
                    if self.log_viewer:
                        _pre_ms = (_t.perf_counter() - _pre_start) * 1000.0
                        self.log_viewer.log_info(f"⏱ 步骤: 预处理 | 文件: {os.path.basename(image_path)} | 用时: {_pre_ms:.1f}ms")
                    
                    # 使用try-catch包装OCR调用
                    try:
                        if self.log_viewer:
                            self.log_viewer.log_ocr_start(image_path)
                            self.log_viewer.log_info(f"🔍 开始OCR处理: {os.path.basename(image_path)}")
                            self.log_viewer.log_info(f"🔍 图片路径: {normalized_path}")
                            self.log_viewer.log_info(f"🔍 图片尺寸: {image.size}")
                            self.log_viewer.log_info(f"🔍 图片模式: {image.mode}")
                            # 保留：无性能计时
                        
                        # 记录图片大小信息
                        if self.log_viewer:
                            self.log_viewer.log_info(f"处理图片: {os.path.basename(image_path)} | 尺寸: {image.size} | 模式: {image.mode}")
                        
                        # 添加超时机制，防止CPU缓存溢出
                        import threading
                        import time
                        
                        # Windows兼容的超时机制
                        timeout_occurred = False
                        
                        def timeout_handler():
                            nonlocal timeout_occurred
                            timeout_occurred = True
                        
                        # 设置15秒超时（缩短时间防止CPU长时间满载）
                        timer = threading.Timer(500.0, timeout_handler)
                        timer.start()
                        
                        try:
                            if self.log_viewer:
                                self.log_viewer.log_info("🔍 调用PaddleOCR.ocr()方法...")
                            _ocr_start = _t.perf_counter()
                            # 使用predict()方法，优先传入内存数组以减少磁盘IO
                            import numpy as np
                            if 'resized_image' in locals():
                                img_for_ocr = resized_image
                            else:
                                img_for_ocr = image
                            if img_for_ocr.mode != 'RGB':
                                img_for_ocr = img_for_ocr.convert('RGB')
                            img_array = np.array(img_for_ocr)
                            ocr_result = self.paddle_ocr.ocr(img_array)
                            # 记录OCR推理耗时
                            if self.log_viewer:
                                _ocr_ms = (_t.perf_counter() - _ocr_start) * 1000.0
                                self.log_viewer.log_info(f"⏱ 步骤: OCR推理 | 文件: {os.path.basename(image_path)} | 用时: {_ocr_ms:.1f}ms")
                            
                            if self.log_viewer:
                                self.log_viewer.log_info(f"✅ OCR调用成功，结果类型: {type(ocr_result)}")
                            
                            if timeout_occurred:
                                raise TimeoutError("OCR处理超时")
                                
                        finally:
                            timer.cancel()  # 取消超时
                        
                        if self.log_viewer:
                            self.log_viewer.log_ocr_complete(image_path)
                            
                    except TimeoutError:
                        error_msg = "OCR处理超时，可能是CPU缓存溢出"
                        if self.log_viewer:
                            self.log_viewer.log_info(f"⏰ 处理超时: {os.path.basename(image_path)}")
                            self.log_viewer.log_ocr_call(image_path, False, 0, error_msg)
                        return f"[{error_msg}]"
                    except Exception as ocr_error:
                        # 获取详细的错误信息
                        import traceback
                        error_type = type(ocr_error).__name__
                        error_msg = str(ocr_error)
                        stack_trace = traceback.format_exc()
                        
                        if self.log_viewer:
                            self.log_viewer.log_info(f"❌ OCR处理失败: {error_type}")
                            self.log_viewer.log_info(f"❌ 错误信息: {error_msg}")
                            self.log_viewer.log_info(f"❌ 堆栈跟踪: {stack_trace}")
                        
                        # 记录详细错误信息到日志
                        if self.log_viewer:
                            self.log_viewer.log_detailed_error(image_path, error_type, error_msg, stack_trace)
                        
                        # 检查是否是CPU缓存溢出相关错误
                        if "memory" in error_msg.lower() or "cache" in error_msg.lower() or "overflow" in error_msg.lower():
                            if self.log_viewer:
                                self.log_viewer.log_info(f"⚠️ 疑似CPU缓存溢出: {os.path.basename(image_path)}")
                        
                        # 检查是否是pipeline相关错误
                        if "pipeline" in error_msg.lower() or "does not exist" in error_msg.lower():
                            if self.log_viewer:
                                self.log_viewer.log_info("⚠️ 疑似PaddleOCR pipeline配置问题")
                                self.log_viewer.log_info("🔍 请检查PaddleOCR的字典文件和模型文件是否正确打包")
                        
                        error_details = f"PaddleOCR error: {error_msg}"
                        if self.log_viewer:
                            self.log_viewer.log_ocr_call(image_path, False, 0, error_details)
                        return f"[{error_details}]"
                    
                    # 添加调试信息
                    if self.log_viewer:
                        self.log_viewer.log_info(f"🔍 OCR结果结构: {type(ocr_result)}, 长度: {len(ocr_result) if ocr_result else 0}")
                        if ocr_result and len(ocr_result) > 0:
                            self.log_viewer.log_info(f"🔍 第一个元素类型: {type(ocr_result[0])}")
                            if isinstance(ocr_result[0], dict) and 'rec_texts' in ocr_result[0]:
                                self.log_viewer.log_info(f"🔍 识别到的文本: {ocr_result[0]['rec_texts']}")
                    
                    texts = []
                    
                    # 解析OCR结果 - 根据日志显示的OCRResult对象结构
                    if ocr_result and len(ocr_result) > 0:
                        for page_result in ocr_result:
                            try:
                                # 根据日志，OCRResult对象有texts属性
                                if hasattr(page_result, 'texts') and page_result.texts:
                                    if isinstance(page_result.texts, list):
                                        for text in page_result.texts:
                                            if text and str(text).strip():
                                                texts.append(str(text).strip())
                                    else:
                                        if str(page_result.texts).strip():
                                            texts.append(str(page_result.texts).strip())
                                # 备用方案：尝试其他可能的属性
                                elif hasattr(page_result, 'text') and page_result.text:
                                    if str(page_result.text).strip():
                                        texts.append(str(page_result.text).strip())
                                elif hasattr(page_result, 'content') and page_result.content:
                                    if str(page_result.content).strip():
                                        texts.append(str(page_result.content).strip())
                                # 如果还是字典格式
                                elif isinstance(page_result, dict) and 'rec_texts' in page_result:
                                    for text in page_result['rec_texts']:
                                        if text and str(text).strip():
                                            texts.append(str(text).strip())
                                # 旧格式：[[box, (text, score)], ...]
                                elif isinstance(page_result, list):
                                    for line in page_result:
                                        if line and len(line) == 2:
                                            text, score = line[1]
                                            if text and str(text).strip():
                                                texts.append(str(text).strip())
                            except Exception as e:
                                if self.log_viewer:
                                    self.log_viewer.log_info(f"⚠️ 解析页面结果失败: {type(page_result)} | 错误: {e}")
                                continue
                    
                    result_text = " ".join(texts).strip()
                    
                    # 记录OCR调用成功
                    if self.log_viewer:
                        self.log_viewer.log_ocr_call(image_path, True, len(result_text))
                        self.log_viewer.log_ocr_result_processing(len(texts))
                        # 记录文本提取（带来源标识）
                        filename = os.path.basename(image_path)
                        folder = os.path.basename(os.path.dirname(image_path))
                        self.log_viewer.log_text_extraction(folder, filename, result_text, True)
                        self.log_viewer.log_processing_complete(image_path, len(result_text))
                        # 记录总耗时
                        _total_ms = (_t.perf_counter() - _total_start) * 1000.0
                        self.log_viewer.log_info(f"⏱ 步骤: 总用时 | 文件: {os.path.basename(image_path)} | 用时: {_total_ms:.1f}ms")
                    
                    return result_text if result_text else "[No text detected]"
                    
                except Exception as e:
                    # Fall back to pytesseract or placeholder on error
                    error_msg = f"PaddleOCR error: {str(e)}"
                    if self.log_viewer:
                        self.log_viewer.log_ocr_call(image_path, False, 0, error_msg)
                    return f"[{error_msg}]"
                finally:
                    # 清理临时文件
                    if temp_file_path and os.path.exists(temp_file_path):
                        try:
                            os.remove(temp_file_path)
                            if self.log_viewer:
                                self.log_viewer.log_temp_file_cleaned(os.path.basename(temp_file_path))
                        except Exception as e:
                            if self.log_viewer:
                                self.log_viewer.log_temp_file_cleanup_failed(str(e))
            else:
                if not self.ocr_error_shown:
                    self.master.after(0, lambda: messagebox.showwarning(
                        "OCR Unavailable",
                        "No OCR engine is installed. Please install the 'paddleocr' package."
                    ))
                    self.ocr_error_shown = True
                placeholder_text = "[OCR not available. Please install paddleocr.]"
                if self.log_viewer:
                    self.log_viewer.log_ocr_call(image_path, False, 0, "OCR引擎未安装")
                return placeholder_text
                
        except Exception as e:
            # 捕获所有未预期的异常
            error_msg = f"Unexpected error in OCR processing: {str(e)}"
            if self.log_viewer:
                self.log_viewer.log_ocr_call(image_path, False, 0, error_msg)
            return f"[{error_msg}]"
        finally:
            # 确保临时文件被清理
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                except:
                    pass  # 忽略清理错误

    def _is_image_file(self, filename: str) -> bool:
        ext = os.path.splitext(filename)[1].lower()
        is_image = ext in {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp"}
        if self.log_viewer and not is_image:
            # 记录非图片文件，帮助调试
            self.log_viewer.log_info(f"📄 跳过非图片文件: {filename}")
        return is_image

    def _build_aggregated_text(self) -> None:
        """构建包含每个文件夹标题的单个聚合文本字符串。
        聚合文本存储在 `self.aggregated_text` 中。
        """
        lines: List[str] = []
        # 按文件夹然后按文件名排序以保持顺序
        sorted_records = sorted(self.records, key=lambda r: (r.folder, r.filename))
        current_folder: Optional[str] = None
        for record in sorted_records:
            if record.folder != current_folder:
                # 新文件夹标题
                if current_folder is not None:
                    lines.append("")  # 文件夹之间的空行
                heading = f"### {record.folder}"
                lines.append(heading)
                current_folder = record.folder
            lines.append(record.text)
        self.aggregated_text = "\n".join(lines)

    # ------------------------------------------------------------------
    # 搜索和结果显示
    #
    def perform_search(self) -> None:
        keyword = self.keyword_entry.get().strip()
        if not keyword:
            messagebox.showinfo("提示", "请输入搜索关键词")
            return
            
        filter_folder = self.selected_folder.strip()
        results = []
        
        for record in self.records:
            # 文件夹过滤
            if filter_folder:
                # 支持多级文件夹匹配 - 包括子文件夹
                if not (record.folder == filter_folder or 
                       record.folder.startswith(filter_folder + "\\") or 
                       record.folder.endswith("\\" + filter_folder) or
                       # 新增：检查是否在指定文件夹的任意子文件夹中
                       self._is_in_folder_or_subfolders(record.folder, filter_folder)):
                    continue
            
            # 关键词搜索
            if keyword.lower() in record.text.lower():
                results.append(record)
        
        # 记录搜索操作
        if self.log_viewer:
            self.log_viewer.log_search(keyword, filter_folder, len(results))
            
        if not results:
            messagebox.showinfo("无匹配", "未找到匹配的文本。")
        else:
            # 清除之前的结果
            for item in self.results_tree.get_children():
                self.results_tree.delete(item)

            for record in results:
                # 提取关键词周围的文本片段作为上下文
                index = record.text.lower().find(keyword.lower())
                start = max(0, index - 30)
                end = min(len(record.text), index + len(keyword) + 30)
                snippet = record.text[start:end].replace('\n', ' ')
                self.results_tree.insert('', 'end', values=(record.folder, record.filename, snippet))

    def on_result_double_click(self, event) -> None:
        item_id = self.results_tree.focus()
        if not item_id:
            return
        values = self.results_tree.item(item_id, 'values')
        if len(values) < 3:
            return
        folder, filename, _snippet = values
        # Find the corresponding record
        record = next((r for r in self.records if r.folder == folder and r.filename == filename), None)
        if not record:
            return
        # Show a new window with the full text and image
        self._show_record_window(record)

    def _show_record_window(self, record: Record) -> None:
        win = tk.Toplevel(self.master)
        win.title(f"{record.folder} - {record.filename}")
        win.geometry("1000x700")
        # 左右分栏：左侧图像（可缩放/拖拽），右侧文本
        image_frame = ttk.Frame(win)
        image_frame.pack(side="left", fill="both", expand=True)
        text_frame = ttk.Frame(win)
        text_frame.pack(side="right", fill="both", expand=True)

        # 可缩放/拖拽的图像查看器
        class ZoomPanImage:
            def __init__(self, parent: tk.Widget, image_path: str):
                self.parent = parent
                self.canvas = tk.Canvas(parent, background="#222")
                self.canvas.pack(fill="both", expand=True)
                # 鼠标手势状态
                self.is_dragging = False
                self.last_x = 0
                self.last_y = 0
                # 载入原图
                self.original_image = Image.open(image_path).convert('RGB')
                self.original_image= ImageOps.exif_transpose(self.original_image)
                self.current_scale = 1.0
                self.min_scale = 0.1
                self.max_scale = 8.0
                # 画布图像项
                self.tk_image = None
                self.image_item = None
                # 平移偏移量（相对画布中心）
                self.offset_x = 0
                self.offset_y = 0

                # 绑定事件
                self.canvas.bind("<Configure>", self._on_resize)
                self.canvas.bind("<Enter>", self._on_enter)
                self.canvas.bind("<Leave>", self._on_leave)
                self.canvas.bind("<ButtonPress-1>", self._on_button_press)
                self.canvas.bind("<B1-Motion>", self._on_mouse_drag)
                self.canvas.bind("<ButtonRelease-1>", self._on_button_release)
                # 滚轮缩放（Windows/macOS）
                self.canvas.bind("<MouseWheel>", self._on_mousewheel)
                # 滚轮缩放（Linux）
                self.canvas.bind("<Button-4>", lambda e: self._zoom_at(1.1, e.x, e.y))
                self.canvas.bind("<Button-5>", lambda e: self._zoom_at(0.9, e.x, e.y))

                self._redraw()

            def _on_resize(self, event):
                self._redraw()

            def _on_enter(self, _event):
                # 悬停：小手
                self.canvas.config(cursor='hand2')

            def _on_leave(self, _event):
                self.canvas.config(cursor='')

            def _on_button_press(self, event):
                self.is_dragging = True
                self.last_x, self.last_y = event.x, event.y
                # 拖拽中：抓握形状（跨平台用 sizeall/fleur 作为替代）
                try:
                    self.canvas.config(cursor='fleur')
                except Exception:
                    self.canvas.config(cursor='sizeall')

            def _on_mouse_drag(self, event):
                if not self.is_dragging:
                    return
                dx = event.x - self.last_x
                dy = event.y - self.last_y
                self.last_x, self.last_y = event.x, event.y
                self.offset_x += dx
                self.offset_y += dy
                self._update_image_position()

            def _on_button_release(self, _event):
                self.is_dragging = False
                # 释放后恢复小手
                self.canvas.config(cursor='hand2')

            def _on_mousewheel(self, event):
                # Windows: event.delta 正负120；macOS: 可能为较小值
                if event.delta > 0:
                    scale_factor = 1.1
                else:
                    scale_factor = 0.9
                self._zoom_at(scale_factor, event.x, event.y)

            def _zoom_at(self, factor: float, x: int, y: int):
                new_scale = max(self.min_scale, min(self.max_scale, self.current_scale * factor))
                if abs(new_scale - self.current_scale) < 1e-6:
                    return
                # 为了在鼠标位置缩放，计算缩放前鼠标指向的图像坐标，缩放后维持该点在同一画布位置
                cx, cy = self._canvas_center()
                # 画布坐标转为当前图像坐标（考虑偏移与缩放）
                img_x_before = (x - cx - self.offset_x) / self.current_scale
                img_y_before = (y - cy - self.offset_y) / self.current_scale
                self.current_scale = new_scale
                # 缩放后，重新计算需要的offset使该图像点仍落在(x,y)
                self.offset_x = x - cx - img_x_before * self.current_scale
                self.offset_y = y - cy - img_y_before * self.current_scale
                self._redraw()

            def _canvas_center(self):
                w = max(1, self.canvas.winfo_width())
                h = max(1, self.canvas.winfo_height())
                return w // 2, h // 2

            def _render_scaled_image(self):
                # 依据当前缩放与画布大小，生成显示图像
                base_w, base_h = self.original_image.size
                disp_w = max(1, int(base_w * self.current_scale))
                disp_h = max(1, int(base_h * self.current_scale))
                # 为避免超大图耗内存，限制到 4000 像素边长
                max_edge = 4000
                ratio = min(max_edge / max(disp_w, disp_h), 1.0)
                if ratio < 1.0:
                    disp_w = max(1, int(disp_w * ratio))
                    disp_h = max(1, int(disp_h * ratio))
                img = self.original_image.resize((disp_w, disp_h), Image.LANCZOS)
                self.tk_image = ImageTk.PhotoImage(img)
                return self.tk_image

            def _update_image_position(self):
                if self.image_item is not None:
                    cx, cy = self._canvas_center()
                    self.canvas.coords(self.image_item, cx + self.offset_x, cy + self.offset_y)

            def _redraw(self):
                # 直接重绘，避免复杂的延迟机制
                tk_img = self._render_scaled_image()
                cx, cy = self._canvas_center()
                if self.image_item is None:
                    self.image_item = self.canvas.create_image(cx + self.offset_x, cy + self.offset_y, image=tk_img)
                else:
                    self.canvas.itemconfigure(self.image_item, image=tk_img)
                    self._update_image_position()
                # 保持引用，防止被GC
                self.canvas.image = tk_img

        # 创建图像查看器
        try:
            ZoomPanImage(image_frame, record.filepath)
        except Exception as e:
            ttk.Label(image_frame, text=f"Error loading image: {e}").pack()

        # 文本显示
        text_widget = tk.Text(text_frame, wrap='word')
        text_widget.insert('1.0', record.text)
        text_widget.config(state='disabled')
        text_widget.pack(fill='both', expand=True)


    # ------------------------------------------------------------------
    # 导出聚合文本
    #
    def export_text(self) -> None:
        if not self.aggregated_text:
            messagebox.showinfo("无内容导出", "还没有聚合任何文本。请先导入一个案件。")
            return
        file_path = filedialog.asksaveasfilename(
            title="保存聚合文本", defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        if not file_path:
            return
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(self.aggregated_text)
            messagebox.showinfo("导出成功", f"聚合文本已保存到 {file_path}")
            # 记录导出成功
            if self.log_viewer:
                self.log_viewer.log_export(file_path, True)
        except Exception as e:
            messagebox.showerror("导出失败", f"无法保存文件: {e}")
            # 记录导出失败
            if self.log_viewer:
                self.log_viewer.log_paddleocr_init_failed(str(e))

    def show_folder_menu(self):
        # 弹出多级菜单选择文件夹
        if not hasattr(self, 'folder_tree') or not self.folder_tree:
            messagebox.showinfo("提示", "请先导入案件/图片")
            return
        
        menu = tk.Menu(self.master, tearoff=0)
        
        # 添加"全部文件夹"选项
        menu.add_command(label="🔍 全部文件夹", command=lambda: self.on_folder_selected(""))
        menu.add_separator()
        
        def build_menu(menu, tree, parent_path=""):
            for folder, subfolders in tree.items():
                full_path = os.path.join(parent_path, folder) if parent_path else folder
                if subfolders:
                    # 有子文件夹的情况
                    submenu = tk.Menu(menu, tearoff=0)
                    build_menu(submenu, subfolders, full_path)
                    
                    # 检查子菜单是否有内容
                    submenu_items = []
                    try:
                        for i in range(submenu.index('end') + 1):
                            submenu_items.append(submenu.entrycget(i, 'label'))
                    except:
                        pass
                    
                    # 只有当子菜单有内容时才添加cascade菜单
                    if submenu_items:
                        menu.add_cascade(label=f"📁 {folder}", menu=submenu)
                    
                    # 添加当前文件夹的选项（可以查看当前文件夹下的图片）
                    menu.add_command(label=f"📄 {folder} (当前)", command=lambda p=full_path: self.on_folder_selected(p))
                else:
                    # 没有子文件夹的情况
                    menu.add_command(label=f"📄 {folder}", command=lambda p=full_path: self.on_folder_selected(p))
        
        build_menu(menu, self.folder_tree)
        
        # 在按钮下方弹出
        x = self.master.winfo_pointerx()
        y = self.master.winfo_pointery()
        menu.tk_popup(x, y)

    def on_folder_selected(self, folder_path):
        self.selected_folder = folder_path
        
        # 记录文件夹选择日志
        if self.log_viewer:
            if folder_path:
                self.log_viewer.log_info(f"📁 用户选择文件夹: {folder_path}")
            else:
                self.log_viewer.log_info("📁 用户选择: 全部文件夹")
        
        # 显示当前选择的文件夹
        if folder_path:
            self.status_var.set(f"已选择文件夹: {folder_path}")
        else:
            self.status_var.set("已选择: 全部文件夹")
        
        # 显示该文件夹下的图片预览
        self.show_folder_images(folder_path)
    
    def show_folder_images(self, folder_path):
        """显示指定文件夹下的图片预览"""
        # 清空之前的结果
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
        
        if not folder_path:
            # 显示所有图片
            for record in self.records:
                snippet = record.text[:100] + "..." if len(record.text) > 100 else record.text
                self.results_tree.insert('', 'end', values=(record.folder, record.filename, snippet))
        else:
            # 显示指定文件夹及其子文件夹下的所有图片
            for record in self.records:
                # 匹配文件夹路径 - 包括子文件夹
                if (record.folder == folder_path or 
                    record.folder.startswith(folder_path + "\\") or 
                    record.folder.endswith("\\" + folder_path) or
                    # 新增：检查是否在指定文件夹的任意子文件夹中
                    self._is_in_folder_or_subfolders(record.folder, folder_path)):
                    snippet = record.text[:100] + "..." if len(record.text) > 100 else record.text
                    self.results_tree.insert('', 'end', values=(record.folder, record.filename, snippet))
    
    def _is_in_folder_or_subfolders(self, record_folder, target_folder):
        """检查record_folder是否在target_folder或其子文件夹中"""
        # 将路径分割成组件
        record_parts = record_folder.split('\\')
        target_parts = target_folder.split('\\')
        
        # 如果target_folder是record_folder的前缀，说明record_folder在target_folder的子文件夹中
        if len(record_parts) > len(target_parts):
            # 检查target_parts是否是record_parts的前缀
            for i, target_part in enumerate(target_parts):
                if i >= len(record_parts) or record_parts[i] != target_part:
                    return False
            return True
        
        return False


def main() -> None:
    root = tk.Tk()
    app = CaseManagerApp(root)
    root.mainloop()


if __name__ == "__main__":
    try:
        # 初始化日志系统
        from log_viewer import get_log_viewer
        log_viewer = get_log_viewer()
        
        if log_viewer:
            log_viewer.log_info("🚀 正在启动OCR案件管理系统...")
            log_viewer.log_info("=" * 50)
            log_viewer.log_info("🔍 系统信息:")
            import sys
            log_viewer.log_info(f"Python版本: {sys.version}")
            log_viewer.log_info(f"Python路径: {sys.executable}")
            log_viewer.log_info(f"工作目录: {os.getcwd()}")
            log_viewer.log_info("=" * 50)
        
        main()
        
        if log_viewer:
            log_viewer.log_info("✅ 程序启动完成")
            
    except Exception as e:
        # 如果日志系统不可用，使用print
        print(f"❌ 程序启动失败: {e}")
        import traceback
        traceback.print_exc()