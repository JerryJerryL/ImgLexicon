"""
日志查看器模块
==============

提供日志记录、查看、保存功能，用于调试和监控OCR程序运行状态。
"""

import os
import sys
import logging
import datetime
from typing import Optional, List
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk


class LogViewer:
    """日志查看器类，负责日志的写入、查看和管理"""
    
    def __init__(self, log_dir: str = "logs"):
        """
        初始化日志查看器
        
        Parameters
        ----------
        log_dir : str
            日志文件保存目录
        """
        # 将日志目录固定到可写的应用目录下（兼容打包/工作目录变化）
        try:
            app_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        except Exception:
            app_dir = os.getcwd()
        self.log_dir = os.path.join(app_dir, log_dir)
        self._ensure_log_dir()
        self._setup_logger()
        
    def _ensure_log_dir(self):
        """确保日志目录存在"""
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
            
    def _setup_logger(self):
        """设置独立日志记录器，避免与根日志器互相影响"""
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        log_file = os.path.join(self.log_dir, f"ocr_case_manager_{today}.log")

        self.logger = logging.getLogger('ocr_case_manager')
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False

        # 清理旧的 handlers，避免重复写入
        for h in list(self.logger.handlers):
            try:
                h.close()
            except Exception:
                pass
            self.logger.removeHandler(h)

        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        stream_handler = logging.StreamHandler()
        fmt = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
        file_handler.setFormatter(fmt)
        stream_handler.setFormatter(fmt)
        self.logger.addHandler(file_handler)
        self.logger.addHandler(stream_handler)

    def _flush_handlers(self):
        """立即将日志刷盘，避免UI读取到空内容"""
        try:
            # 刷新独立日志器的 handlers
            for handler in self.logger.handlers:
                try:
                    handler.flush()
                except Exception:
                    pass
            # 兜底刷新根日志器（如果外部仍有写入）
            for handler in logging.getLogger().handlers:
                try:
                    handler.flush()
                except Exception:
                    pass
        except Exception:
            pass
        
    def log_paddleocr_status(self, available: bool, error_msg: str = ""):
        """
        记录PaddleOCR状态
        
        Parameters
        ----------
        available : bool
            PaddleOCR是否可用
        error_msg : str
            错误信息（如果有）
        """
        if available:
            self.logger.info("✅ PaddleOCR 启动成功")
        else:
            self.logger.error(f"❌ PaddleOCR 启动失败: {error_msg}")
            
    def log_ocr_call(self, image_path: str, success: bool, text_length: int = 0, error_msg: str = ""):
        """
        记录OCR调用状态
        
        Parameters
        ----------
        image_path : str
            图片路径
        success : bool
            是否成功
        text_length : int
            提取文本长度
        error_msg : str
            错误信息
        """
        if success:
            self.logger.info(f"✅ OCR调用成功: {os.path.basename(image_path)} -> 提取文本长度: {text_length}")
        else:
            self.logger.error(f"❌ OCR调用失败: {os.path.basename(image_path)} -> {error_msg}")
            
    def log_text_extraction(self, folder: str, filename: str, text: str, has_id: bool = True):
        """
        记录文本提取结果
        
        Parameters
        ----------
        folder : str
            文件夹名（文档类型）
        filename : str
            文件名
        text : str
            提取的文本
        has_id : bool
            是否有来源标识
        """
        status = "✅" if has_id else "⚠️"
        self.logger.info(f"{status} 文本提取: {folder}/{filename} -> 长度: {len(text)} 字符")
        
    def log_case_import(self, case_name: str, total_images: int):
        """记录案件导入"""
        self.logger.info(f"📁 案件导入: {case_name} -> 总图片数: {total_images}")
        
    def log_search(self, keyword: str, filter_term: str, matches: int):
        """记录搜索操作"""
        filter_info = f" (限定: {filter_term})" if filter_term else ""
        self.logger.info(f"🔍 搜索: '{keyword}'{filter_info} -> 匹配结果: {matches} 条")
        
    def log_export(self, file_path: str, success: bool, error_msg: str = ""):
        """记录导出操作"""
        if success:
            self.logger.info(f"💾 导出成功: {file_path}")
        else:
            self.logger.error(f"❌ 导出失败: {file_path} -> {error_msg}")
            
    def log_error(self, error_msg: str, context: str = ""):
        """记录错误"""
        context_info = f" [{context}]" if context else ""
        self.logger.error(f"❌ 错误{context_info}: {error_msg}")
        self._flush_handlers()
        
    def log_info(self, message: str):
        """记录一般信息"""
        self.logger.info(f"ℹ️ {message}")
        self._flush_handlers()

    # 动作事件日志（与流程保持一致）
    def log_resize_image(self, src_path: str, dst_path: str, old_size: tuple, new_size: tuple):
        try:
            src = os.path.basename(src_path)
            dst = os.path.basename(dst_path)
        except Exception:
            src = str(src_path)
            dst = str(dst_path)
        self.logger.info(f"🛠 动作: 调整尺寸 | 源: {src} | 尺寸: {old_size} -> {new_size} | 目标: {dst}")
        self._flush_handlers()

    def log_ocr_action_start(self, image_path: str):
        try:
            name = os.path.basename(image_path)
        except Exception:
            name = str(image_path)
        self.logger.info(f"📝 动作: 提取文字开始 | 文件: {name}")
        self._flush_handlers()

    def log_ocr_action_done(self, image_path: str, text_length: int, elapsed_ms: float):
        try:
            name = os.path.basename(image_path)
        except Exception:
            name = str(image_path)
        self.logger.info(f"📝 动作: 提取文字完成 | 文件: {name} | 文本长度: {text_length} | 用时: {elapsed_ms:.1f}ms")
        self._flush_handlers()

    # （移除性能日志接口以避免干扰主日志）

    def log_paddleocr_init_start(self):
        """记录PaddleOCR初始化开始"""
        self.logger.info("🔄 正在初始化PaddleOCR...")
        
    def log_paddleocr_test_start(self):
        """记录PaddleOCR测试开始"""
        self.logger.info("🧪 测试PaddleOCR功能...")
        
    def log_paddleocr_init_success(self):
        """记录PaddleOCR初始化成功"""
        self.logger.info("✅ PaddleOCR初始化成功并测试通过")
        
    def log_paddleocr_init_failed(self, error_msg: str):
        """记录PaddleOCR初始化失败"""
        self.logger.error(f"❌ PaddleOCR初始化失败: {error_msg}")
        
    def log_image_processing_start(self, image_path: str):
        """记录图片处理开始"""
        self.logger.info(f"🖼️ 开始处理图片: {os.path.basename(image_path)}")
        
    def log_image_info(self, image_path: str, size: tuple, mode: str):
        """记录图片信息"""
        self.logger.info(f"📊 图片信息: {os.path.basename(image_path)} | 尺寸: {size} | 模式: {mode}")
        
    def log_image_format_conversion(self, image_path: str, target_format: str):
        """记录图片格式转换"""
        self.logger.info(f"🔄 图片格式转换: {os.path.basename(image_path)} -> {target_format}")
        
    def log_image_resize(self, original_size: tuple, new_size: tuple, ratio: float):
        """记录图片缩放信息"""
        self.logger.info(f"📏 图片缩放: {original_size} -> {new_size} | 缩放比例: {ratio:.2f}")
        
    def log_temp_file_created(self, filename: str, size_kb: float):
        """记录临时文件创建"""
        self.logger.info(f"📁 临时文件创建: {filename} | 大小: {size_kb:.1f}KB")
        
    def log_temp_file_cleaned(self, filename: str):
        """记录临时文件清理"""
        self.logger.info(f"🧹 临时文件已清理: {filename}")
        
    def log_temp_file_cleanup_failed(self, error_msg: str):
        """记录临时文件清理失败"""
        self.logger.error(f"❌ 清理临时文件失败: {error_msg}")
        
    def log_ocr_start(self, image_path: str):
        """记录OCR识别开始"""
        self.logger.info(f"🔍 开始OCR识别: {os.path.basename(image_path)}")
        
    def log_ocr_complete(self, image_path: str):
        """记录OCR识别完成"""
        self.logger.info(f"✅ OCR识别完成: {os.path.basename(image_path)}")
        
    def log_file_not_found(self, image_path: str):
        """记录文件未找到"""
        self.logger.error(f"❌ 图片文件未找到: {image_path}")
        
    def log_image_open_failed(self, image_path: str, error_msg: str):
        """记录图片打开失败"""
        self.logger.error(f"❌ 图片打开/验证失败: {os.path.basename(image_path)} -> {error_msg}")
        
    def log_image_zero_dimensions(self, image_path: str):
        """记录图片尺寸为零"""
        self.logger.error(f"❌ 图片尺寸为零: {os.path.basename(image_path)}")
        
    def log_paddleocr_not_initialized(self):
        """记录PaddleOCR未正确初始化"""
        self.logger.error("❌ PaddleOCR未正确初始化")
        
    def log_ocr_no_text_detected(self):
        """记录未检测到文本"""
        self.logger.info("ℹ️ 未检测到文本内容")
        
    def log_ocr_result_processing(self, text_count: int):
        """记录OCR结果处理"""
        self.logger.info(f"📝 处理OCR结果: 提取到 {text_count} 个文本区域")
        
    def log_processing_complete(self, image_path: str, text_length: int):
        """记录处理完成"""
        self.logger.info(f"🎉 处理完成: {os.path.basename(image_path)} | 文本长度: {text_length} 字符")
        
    def log_detailed_error(self, image_path: str, error_type: str, error_msg: str, stack_trace: str = ""):
        """记录详细的错误信息"""
        self.logger.error(f"❌ 详细错误: {os.path.basename(image_path)} | 类型: {error_type} | 信息: {error_msg}")
        if stack_trace:
            self.logger.error(f"📋 堆栈跟踪: {stack_trace}")
            
    def log_cpu_memory_info(self, image_path: str, cpu_usage: str = "", memory_usage: str = ""):
        """记录CPU和内存使用情况"""
        info_parts = [f"💻 系统资源: {os.path.basename(image_path)}"]
        if cpu_usage:
            info_parts.append(f"CPU: {cpu_usage}")
        if memory_usage:
            info_parts.append(f"内存: {memory_usage}")
        self.logger.info(" | ".join(info_parts))


class LogWindow:
    """日志查看窗口"""
    
    def __init__(self, parent, log_viewer: LogViewer):
        """
        初始化日志窗口
        
        Parameters
        ----------
        parent : tk.Tk
            父窗口
        log_viewer : LogViewer
            日志查看器实例
        """
        self.parent = parent
        self.log_viewer = log_viewer
        self.window = None
        
    def show(self):
        """显示日志窗口"""
        if self.window is None or not self.window.winfo_exists():
            self._create_window()
        else:
            self.window.lift()  # 窗口已存在，提到前面
            self._refresh_log()
            
    def _create_window(self):
        """创建日志窗口"""
        self.window = tk.Toplevel(self.parent)
        self.window.title("日志查看")
        self.window.geometry("800x600")
        
        # 创建工具栏
        toolbar = ttk.Frame(self.window)
        toolbar.pack(fill="x", padx=5, pady=5)
        
        # 刷新按钮
        refresh_btn = ttk.Button(toolbar, text="刷新", command=self._refresh_log)
        refresh_btn.pack(side="left", padx=5)
        
        # 保存按钮
        save_btn = ttk.Button(toolbar, text="保存日志", command=self._save_log)
        save_btn.pack(side="left", padx=5)
        
        # 清空按钮
        clear_btn = ttk.Button(toolbar, text="清空显示", command=self._clear_display)
        clear_btn.pack(side="left", padx=5)
        
        # 日志级别过滤
        ttk.Label(toolbar, text="日志级别:").pack(side="left", padx=(20, 5))
        self.level_var = tk.StringVar(value="ALL")
        level_combo = ttk.Combobox(toolbar, textvariable=self.level_var, 
                                  values=["ALL", "INFO", "ERROR"], width=10)
        level_combo.pack(side="left", padx=5)
        level_combo.bind("<<ComboboxSelected>>", lambda e: self._refresh_log())

        # 日志类别过滤（新增：性能）
        ttk.Label(toolbar, text="类别:").pack(side="left", padx=(20, 5))
        self.category_var = tk.StringVar(value="全部")
        category_combo = ttk.Combobox(toolbar, textvariable=self.category_var, 
                                      values=["全部", "性能", "常规"], width=10)
        category_combo.pack(side="left", padx=5)
        category_combo.bind("<<ComboboxSelected>>", lambda e: self._refresh_log())
        
        # 创建日志显示区域
        log_frame = ttk.Frame(self.window)
        log_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # 日志文本框
        self.log_text = tk.Text(log_frame, wrap="word", font=("Consolas", 9))
        self.log_text.pack(side="left", fill="both", expand=True)
        
        # 滚动条
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscroll=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        
        # 状态栏
        self.status_var = tk.StringVar()
        status_bar = ttk.Label(self.window, textvariable=self.status_var, relief="sunken")
        status_bar.pack(fill="x", padx=5, pady=2)
        
        # 初始加载日志
        self._refresh_log()
        
    def _refresh_log(self):
        """刷新日志显示"""
        self.log_text.delete(1.0, tk.END)
        
        try:
            # 获取今天的日志文件（主文件）
            today = datetime.datetime.now().strftime("%Y-%m-%d")
            primary = os.path.join(self.log_viewer.log_dir, f"ocr_case_manager_{today}.log")
            candidates = [primary]
            # 兼容旧命名（回退）
            fallback = os.path.join(self.log_viewer.log_dir, f"ocr_log_{today}.log")
            if os.path.exists(fallback):
                candidates.append(fallback)
            # 增加性能专用文件（新的分离文件）
            perf_file = os.path.join(self.log_viewer.log_dir, f"ocr_perf_{today}.log")
            if os.path.exists(perf_file):
                # 性能类别优先展示性能文件
                if self.category_var.get() == "性能":
                    candidates.insert(0, perf_file)
                else:
                    candidates.append(perf_file)
            total_shown = 0
            used_file = None
            level_filter = self.level_var.get()
            category_filter = self.category_var.get()
            
            for lf in candidates:
                if not os.path.exists(lf):
                    continue
                with open(lf, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                filtered_lines = []
                for line in lines:
                    if not (level_filter == "ALL" or level_filter in line):
                        continue
                    if category_filter == "性能" and "[PERF]" not in line:
                        continue
                    if category_filter == "常规" and "[PERF]" in line:
                        continue
                    filtered_lines.append(line)
                if filtered_lines:
                    for line in filtered_lines:
                        self.log_text.insert(tk.END, line)
                    total_shown += len(filtered_lines)
                    used_file = lf
                    break
            if used_file:
                self.status_var.set(f"日志文件: {os.path.basename(used_file)} | 路径: {os.path.abspath(used_file)} | 显示 {total_shown} 行")
            else:
                # 如果没有任何符合过滤的行，显示提示并标出主文件路径
                self.status_var.set(f"日志文件: {os.path.basename(primary)} | 路径: {os.path.abspath(primary)} | 显示 0 行")
                
        except Exception as e:
            self.log_text.insert(tk.END, f"读取日志文件失败: {e}")
            self.status_var.set("读取失败")
            
        # 滚动到底部
        self.log_text.see(tk.END)
        
    def _save_log(self):
        """保存日志到指定位置"""
        try:
            today = datetime.datetime.now().strftime("%Y-%m-%d")
            log_file = os.path.join(self.log_viewer.log_dir, f"ocr_case_manager_{today}.log")
            
            if os.path.exists(log_file):
                save_path = filedialog.asksaveasfilename(
                    title="保存日志文件",
                    defaultextension=".log",
                    filetypes=[("日志文件", "*.log"), ("文本文件", "*.txt"), ("所有文件", "*.*")],
                    initialfile=f"ocr_log_{today}.log"
                )
                
                if save_path:
                    import shutil
                    shutil.copy2(log_file, save_path)
                    messagebox.showinfo("保存成功", f"日志已保存到: {save_path}")
                    self.log_viewer.log_info(f"日志文件已保存到: {save_path}")
            else:
                messagebox.showwarning("无日志文件", "今天还没有日志记录")
                
        except Exception as e:
            messagebox.showerror("保存失败", f"保存日志文件时出错: {e}")
            
    def _clear_display(self):
        """清空显示"""
        self.log_text.delete(1.0, tk.END)
        self.status_var.set("显示已清空")


# 全局日志查看器实例
_log_viewer = None

def get_log_viewer() -> LogViewer:
    """获取全局日志查看器实例"""
    global _log_viewer
    if _log_viewer is None:
        _log_viewer = LogViewer()
    return _log_viewer
