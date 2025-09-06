import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import re
import math

class DraggableLabel(tk.Label):
    def __init__(self, parent, image_path, image_obj, grid_row, grid_col, app, **kwargs):
        super().__init__(parent, **kwargs)
        self.image_path = image_path
        self.image_obj = image_obj
        self.grid_row = grid_row  # 网格行号
        self.grid_col = grid_col  # 网格列号
        self.app = app  # 应用程序引用
        self.original_parent = parent  # 原始父容器
        
        self.bind("<Button-1>", self.on_click)
        self.bind("<B1-Motion>", self.on_drag)
        self.bind("<ButtonRelease-1>", self.on_release)
        
        self._drag_start_x = 0
        self._drag_start_y = 0
        self.is_dragging = False
        
    def on_click(self, event):
        self._drag_start_x = event.x
        self._drag_start_y = event.y
        self.is_dragging = True
        self.lift()  # 将标签置于顶层
        
    def on_drag(self, event):
        if not self.is_dragging:
            return
            
        # 计算新位置
        x = self.winfo_x() + event.x - self._drag_start_x
        y = self.winfo_y() + event.y - self._drag_start_y
        
        # 更新位置
        self.place(x=x, y=y)
        
    def on_release(self, event):
        if not self.is_dragging:
            return
            
        self.is_dragging = False
        
        # 检查是否拖拽到了另一个网格单元上
        if self.app.grid_window and self.app.grid_window.winfo_exists():
            self.app.handle_drop(self, event.x_root, event.y_root)

class PuzzleApp:
    def __init__(self, root):
        self.root = root
        self.root.title("拼图生成器")
        self.root.geometry("1000x700")
        
        self.output_file = tk.StringVar()
        self.rows = tk.IntVar(value=2)
        self.cols = tk.IntVar(value=2)
        self.border = tk.IntVar(value=0)
        self.keep_aspect_ratio = tk.BooleanVar(value=True)
        self.resize_mode = tk.StringVar(value="scale")  # scale, crop
        self.image_paths = []
        self.preview_images = []
        self.puzzle_image = None
        self.puzzle_photo = None
        self.draggable_labels = []  # 存储所有可拖拽标签
        self.grid_cells = []  # 存储所有网格单元
        self.grid_window = None
        self.ordered_image_paths = []  # 存储重新排序后的图片路径
        
        # 绑定行列数变化事件
        self.rows.trace('w', self.on_grid_change)
        self.cols.trace('w', self.on_grid_change)
        
        self.create_widgets()
        
    def natural_sort_key(self, text):
        """自然排序键函数"""
        return [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', text)]
    
    def get_image_files(self, file_paths):
        """获取并排序图片文件"""
        supported_formats = ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff')
        files = [f for f in file_paths if f.lower().endswith(supported_formats)]
        files.sort(key=self.natural_sort_key)
        return files
    
    def resize_image(self, img, target_size, resize_mode="scale", keep_aspect_ratio=True):
        """
        调整单张图片尺寸
        :param img: PIL Image对象
        :param target_size: 目标尺寸 (width, height)
        :param resize_mode: 调整模式 ("scale", "crop")
        :param keep_aspect_ratio: 是否保持纵横比
        :return: 调整后的图片
        """
        if resize_mode == "scale":
            # 缩放模式
            img_copy = img.copy()
            if keep_aspect_ratio:
                # 保持纵横比缩放
                img_copy.thumbnail(target_size, Image.Resampling.LANCZOS)
            else:
                # 拉伸填充整个目标区域
                img_copy = img_copy.resize(target_size, Image.Resampling.LANCZOS)
            return img_copy
        elif resize_mode == "crop":
            # 裁剪模式：居中裁剪并缩放到目标尺寸，忽略keep_aspect_ratio设置
            img_copy = img.copy()
            img_ratio = img_copy.width / img_copy.height
            target_ratio = target_size[0] / target_size[1]
            
            if img_ratio > target_ratio:
                # 图片更宽，裁剪左右
                new_height = img_copy.height
                new_width = int(new_height * target_ratio)
                left = (img_copy.width - new_width) // 2
                top = 0
                right = left + new_width
                bottom = new_height
            else:
                # 图片更高，裁剪上下
                new_width = img_copy.width
                new_height = int(new_width / target_ratio)
                left = 0
                top = (img_copy.height - new_height) // 2
                right = new_width
                bottom = top + new_height
                
            img_copy = img_copy.crop((left, top, right, bottom))
            img_copy = img_copy.resize(target_size, Image.Resampling.LANCZOS)
            return img_copy
        else:
            # 默认缩放模式
            img_copy = img.copy()
            if keep_aspect_ratio:
                img_copy.thumbnail(target_size, Image.Resampling.LANCZOS)
            else:
                img_copy = img_copy.resize(target_size, Image.Resampling.LANCZOS)
            return img_copy
    
    def resize_images(self, image_paths, target_size, resize_mode="scale"):
        """将所有图片调整为指定尺寸"""
        resized_images = []
        keep_aspect_ratio = self.keep_aspect_ratio.get()
        
        for img_path in image_paths:
            try:
                with Image.open(img_path) as img:
                    if resize_mode == "scale":
                        # 缩放模式：创建新图片并居中放置（仅在保持纵横比时）
                        if keep_aspect_ratio:
                            new_img = Image.new('RGB', target_size, (255, 255, 255))
                            resized_img = self.resize_image(img, target_size, resize_mode, keep_aspect_ratio)
                            # 居中放置
                            offset = ((target_size[0] - resized_img.size[0]) // 2, 
                                     (target_size[1] - resized_img.size[1]) // 2)
                            new_img.paste(resized_img, offset)
                            resized_images.append(new_img)
                        else:
                            # 不保持纵横比时直接拉伸填充
                            resized_img = self.resize_image(img, target_size, resize_mode, keep_aspect_ratio)
                            resized_images.append(resized_img)
                    elif resize_mode == "crop":
                        # 裁剪模式：直接使用处理后的图片
                        resized_img = self.resize_image(img, target_size, resize_mode, keep_aspect_ratio)
                        resized_images.append(resized_img)
                    else:
                        # 默认处理
                        if keep_aspect_ratio:
                            new_img = Image.new('RGB', target_size, (255, 255, 255))
                            resized_img = self.resize_image(img, target_size, "scale", keep_aspect_ratio)
                            offset = ((target_size[0] - resized_img.size[0]) // 2, 
                                     (target_size[1] - resized_img.size[1]) // 2)
                            new_img.paste(resized_img, offset)
                            resized_images.append(new_img)
                        else:
                            resized_img = self.resize_image(img, target_size, "scale", keep_aspect_ratio)
                            resized_images.append(resized_img)
            except Exception as e:
                print(f"处理图片 {img_path} 时出错: {e}")
                # 出错时添加空白图片
                if resize_mode == "scale" and keep_aspect_ratio:
                    resized_images.append(Image.new('RGB', target_size, (255, 255, 255)))
                else:
                    resized_images.append(Image.new('RGB', target_size, (255, 255, 255)))
        return resized_images
    
    def create_puzzle(self, image_paths, rows, cols, white_border=0):
        """创建拼图"""
        # 获取最大图片尺寸
        max_width = 0
        max_height = 0
        
        # 先打开所有图片并找出最大尺寸
        valid_images = []
        for path in image_paths:
            try:
                with Image.open(path) as img:
                    max_width = max(max_width, img.width)
                    max_height = max(max_height, img.height)
                    valid_images.append(path)
            except Exception as e:
                print(f"读取图片 {path} 时出错: {e}")
        
        # 如果图片数量不足，用空白图片填充
        total_cells = rows * cols
        needed_blank = total_cells - len(valid_images)
        if needed_blank > 0:
            # 添加空白图片路径占位符
            for _ in range(needed_blank):
                valid_images.append(None)
        
        # 调整所有图片到统一尺寸
        target_size = (max_width, max_height)
        resize_mode = self.resize_mode.get()
        resized_images = []
        
        for img_path in valid_images:
            if img_path is None:
                # 添加空白图片
                if resize_mode == "scale" and self.keep_aspect_ratio.get():
                    resized_images.append(Image.new('RGB', target_size, (255, 255, 255)))
                else:
                    resized_images.append(Image.new('RGB', target_size, (255, 255, 255)))
            else:
                try:
                    with Image.open(img_path) as img:
                        if resize_mode == "scale":
                            # 缩放模式
                            if self.keep_aspect_ratio.get():
                                # 保持纵横比：创建新图片并居中放置
                                new_img = Image.new('RGB', target_size, (255, 255, 255))
                                resized_img = self.resize_image(img, target_size, resize_mode, self.keep_aspect_ratio.get())
                                # 居中放置
                                offset = ((target_size[0] - resized_img.size[0]) // 2, 
                                         (target_size[1] - resized_img.size[1]) // 2)
                                new_img.paste(resized_img, offset)
                                resized_images.append(new_img)
                            else:
                                # 不保持纵横比：直接拉伸填充
                                resized_img = self.resize_image(img, target_size, resize_mode, self.keep_aspect_ratio.get())
                                resized_images.append(resized_img)
                        elif resize_mode == "crop":
                            # 裁剪模式：直接使用处理后的图片
                            resized_img = self.resize_image(img, target_size, resize_mode, self.keep_aspect_ratio.get())
                            resized_images.append(resized_img)
                        else:
                            # 默认处理
                            if self.keep_aspect_ratio.get():
                                new_img = Image.new('RGB', target_size, (255, 255, 255))
                                resized_img = self.resize_image(img, target_size, "scale", self.keep_aspect_ratio.get())
                                offset = ((target_size[0] - resized_img.size[0]) // 2, 
                                         (target_size[1] - resized_img.size[1]) // 2)
                                new_img.paste(resized_img, offset)
                                resized_images.append(new_img)
                            else:
                                resized_img = self.resize_image(img, target_size, "scale", self.keep_aspect_ratio.get())
                                resized_images.append(resized_img)
                except Exception as e:
                    print(f"处理图片 {img_path} 时出错: {e}")
                    # 出错时添加空白图片
                    if resize_mode == "scale" and self.keep_aspect_ratio.get():
                        resized_images.append(Image.new('RGB', target_size, (255, 255, 255)))
                    else:
                        resized_images.append(Image.new('RGB', target_size, (255, 255, 255)))
        
        # 计算最终拼图尺寸
        final_width = cols * max_width + (cols + 1) * white_border
        final_height = rows * max_height + (rows + 1) * white_border
        
        # 创建最终的拼图
        final_image = Image.new('RGB', (final_width, final_height), (255, 255, 255))
        
        # 拼接图片
        for i in range(rows):
            for j in range(cols):
                idx = i * cols + j
                if idx < len(resized_images):
                    x = j * max_width + (j + 1) * white_border
                    y = i * max_height + (i + 1) * white_border
                    final_image.paste(resized_images[idx], (x, y))
        
        return final_image
    
    def browse_images(self):
        """选择多个图片文件"""
        files = filedialog.askopenfilenames(
            title="选择图片文件",
            filetypes=[
                ("图片文件", "*.png *.jpg *.jpeg *.bmp *.gif *.tiff"),
                ("PNG files", "*.png"),
                ("JPEG files", "*.jpg *.jpeg"),
                ("BMP files", "*.bmp"),
                ("GIF files", "*.gif"),
                ("TIFF files", "*.tiff"),
                ("All files", "*.*")
            ]
        )
        
        if files:
            # 添加新选择的图片到现有列表中
            for file in files:
                if file not in self.image_paths:
                    self.image_paths.append(file)
            
            # 更新界面
            self.load_images()
    
    def remove_selected_image(self):
        """移除选中的图片"""
        if not hasattr(self, 'image_listbox'):
            return
            
        selected_indices = list(self.image_listbox.curselection())
        if not selected_indices:
            messagebox.showwarning("警告", "请先选择要移除的图片")
            return
        
        # 从后往前删除，避免索引变化问题
        for i in reversed(selected_indices):
            del self.image_paths[i]
        
        # 更新界面
        self.load_images()
    
    def clear_all_images(self):
        """清空所有图片"""
        if messagebox.askyesno("确认", "确定要清空所有图片吗？"):
            self.image_paths = []
            self.ordered_image_paths = []  # 同时清空重新排序的列表
            self.load_images()
    
    def browse_output(self):
        """选择输出文件"""
        file = filedialog.asksaveasfilename(
            defaultextension=".jpg",
            filetypes=[("JPEG files", "*.jpg"), ("PNG files", "*.png"), ("All files", "*.*")]
        )
        if file:
            self.output_file.set(file)
    
    def load_images(self):
        """加载并预览图片"""
        # 清空之前的预览
        for widget in self.preview_frame.winfo_children():
            widget.destroy()
        
        self.preview_images = []
        
        # 显示图片预览
        if self.image_paths:
            # 创建列表框显示图片文件名
            listbox_frame = ttk.Frame(self.preview_frame)
            listbox_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
            
            ttk.Label(listbox_frame, text="已选择的图片:").pack(anchor=tk.W)
            
            self.image_listbox = tk.Listbox(listbox_frame, selectmode=tk.EXTENDED, height=15)
            scrollbar = ttk.Scrollbar(listbox_frame, orient=tk.VERTICAL, command=self.image_listbox.yview)
            self.image_listbox.configure(yscrollcommand=scrollbar.set)
            
            for path in self.image_paths:
                self.image_listbox.insert(tk.END, os.path.basename(path))
            
            self.image_listbox.pack(side=tk.LEFT, fill=tk.Y)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            # 创建按钮框架
            button_frame = ttk.Frame(listbox_frame)
            button_frame.pack(fill=tk.X, pady=(5, 0))
            
            ttk.Button(button_frame, text="移除选中", command=self.remove_selected_image).pack(side=tk.LEFT, padx=(0, 5))
            ttk.Button(button_frame, text="清空所有", command=self.clear_all_images).pack(side=tk.LEFT)
            
            # 创建预览区域
            preview_area = ttk.Frame(self.preview_frame)
            preview_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            
            # 创建一个滚动区域来显示预览图
            canvas = tk.Canvas(preview_area)
            scrollbar_v = ttk.Scrollbar(preview_area, orient="vertical", command=canvas.yview)
            scrollable_frame = ttk.Frame(canvas)
            
            scrollable_frame.bind(
                "<Configure>",
                lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
            )
            
            canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar_v.set)
            
            # 显示图片
            for i, path in enumerate(self.image_paths):
                try:
                    with Image.open(path) as img:
                        # 创建缩略图
                        img_copy = img.copy()
                        img_copy.thumbnail((100, 100), Image.Resampling.LANCZOS)
                        photo = ImageTk.PhotoImage(img_copy)
                        self.preview_images.append(photo)  # 保持引用
                        
                        # 创建预览标签
                        frame = ttk.Frame(scrollable_frame)
                        frame.grid(row=i//4, column=i%4, padx=5, pady=5)
                        
                        label = ttk.Label(frame, image=photo)
                        label.pack()
                        
                        name_label = ttk.Label(frame, text=os.path.basename(path), 
                                              wraplength=100, justify="center")
                        name_label.pack()
                except Exception as e:
                    print(f"加载预览图 {path} 时出错: {e}")
            
            canvas.pack(side="left", fill="both", expand=True)
            scrollbar_v.pack(side="right", fill="y")
            
            # 更新图片数量显示
            self.image_count_label.config(text=f"已选择 {len(self.image_paths)} 张图片")
            
            # 推荐行列数
            self.recommend_grid()
        else:
            # 没有图片时显示提示
            no_image_label = ttk.Label(self.preview_frame, text="未选择任何图片，请点击上方按钮添加图片")
            no_image_label.pack(expand=True)
            self.image_count_label.config(text="未选择图片")
    
    def recommend_grid(self):
        """推荐行列数"""
        if not self.image_paths:
            return
            
        count = len(self.image_paths)
        # 寻找最接近正方形的行列数
        sqrt_count = math.sqrt(count)
        rows = int(math.ceil(sqrt_count))
        cols = int(math.ceil(count / rows))
        
        self.rows.set(rows)
        self.cols.set(cols)
    
    def on_grid_change(self, *args):
        """行列数变化时更新显示"""
        if not self.image_paths:
            return
            
        count = len(self.image_paths)
        rows = self.rows.get()
        cols = self.cols.get()
        
        if rows > 0 and cols > 0:
            total_cells = rows * cols
            if total_cells >= count:
                needed_blank = total_cells - count
                self.grid_info_label.config(
                    text=f"总共 {total_cells} 格，图片 {count} 张，空白 {needed_blank} 格"
                )
            else:
                self.grid_info_label.config(
                    text=f"总共 {total_cells} 格，图片 {count} 张，图片过多！"
                )
    
    def show_grid_layout(self):
        """显示网格布局窗口"""
        if not self.image_paths:
            messagebox.showerror("错误", "请先选择图片文件")
            return
            
        rows = self.rows.get()
        cols = self.cols.get()
        
        if rows <= 0 or cols <= 0:
            messagebox.showerror("错误", "行数和列数必须大于0")
            return
            
        # 创建网格布局窗口
        if self.grid_window and self.grid_window.winfo_exists():
            self.grid_window.destroy()
            
        self.grid_window = tk.Toplevel(self.root)
        self.grid_window.title("网格布局")
        self.grid_window.geometry("800x600")
        
        # 初始化ordered_image_paths（如果还没有初始化或者图片数量发生变化）
        if not self.ordered_image_paths or len(self.ordered_image_paths) != len(self.image_paths):
            self.ordered_image_paths = self.image_paths.copy()
        
        # 如果图片数量不足，添加空位
        total_cells = rows * cols
        while len(self.ordered_image_paths) < total_cells:
            self.ordered_image_paths.append(None)
        
        # 如果图片过多，截断列表
        if len(self.ordered_image_paths) > total_cells:
            self.ordered_image_paths = self.ordered_image_paths[:total_cells]
        
        # 计算网格尺寸
        cell_width = 100
        cell_height = 100
        grid_width = cols * cell_width
        grid_height = rows * cell_height
        
        # 创建画布
        canvas_frame = ttk.Frame(self.grid_window)
        canvas_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        canvas = tk.Canvas(canvas_frame, width=min(grid_width, 700), height=min(grid_height, 500))
        canvas.pack(side="left", fill="both", expand=True)
        
        # 添加滚动条
        v_scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
        v_scrollbar.pack(side="right", fill="y")
        h_scrollbar = ttk.Scrollbar(self.grid_window, orient="horizontal", command=canvas.xview)
        h_scrollbar.pack(side="bottom", fill="x")
        
        canvas.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # 创建滚动框架
        scrollable_frame = ttk.Frame(canvas)
        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        
        def on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
            
        def on_canvas_configure(event):
            canvas.itemconfig(canvas_window, width=event.width)
            
        scrollable_frame.bind("<Configure>", on_frame_configure)
        canvas.bind("<Configure>", on_canvas_configure)
        
        # 创建网格
        self.draggable_labels = []
        self.grid_cells = []
        for i in range(rows):
            row_cells = []
            for j in range(cols):
                idx = i * cols + j
                
                # 创建网格单元
                cell_frame = tk.Frame(scrollable_frame, width=cell_width, height=cell_height,
                                    relief="solid", bd=1, bg="white")
                cell_frame.grid(row=i, column=j, padx=2, pady=2)
                cell_frame.grid_propagate(False)
                cell_frame.row = i  # 记录行号
                cell_frame.col = j  # 记录列号
                
                row_cells.append(cell_frame)
                
                if idx < len(self.ordered_image_paths) and self.ordered_image_paths[idx]:
                    # 显示图片
                    try:
                        with Image.open(self.ordered_image_paths[idx]) as img:
                            img_copy = img.copy()
                            img_copy.thumbnail((90, 90), Image.Resampling.LANCZOS)
                            photo = ImageTk.PhotoImage(img_copy)
                            
                            label = DraggableLabel(cell_frame, self.ordered_image_paths[idx], photo, 
                                                 i, j, self, image=photo, bd=0)
                            label.image = photo  # 保持引用
                            label.place(relx=0.5, rely=0.5, anchor="center")
                            self.draggable_labels.append(label)
                    except Exception as e:
                        print(f"加载图片时出错: {e}")
                        placeholder = tk.Label(cell_frame, text="错误", bg="lightgray")
                        placeholder.place(relx=0.5, rely=0.5, anchor="center")
                else:
                    # 显示空位
                    placeholder = tk.Label(cell_frame, text="空", bg="lightgray")
                    placeholder.place(relx=0.5, rely=0.5, anchor="center")
            
            self.grid_cells.append(row_cells)
        
        # 按钮区域
        button_frame = ttk.Frame(self.grid_window)
        button_frame.pack(side="bottom", fill="x", padx=10, pady=10)
        
        ttk.Button(button_frame, text="关闭", 
                  command=self.grid_window.destroy).pack(side="right", padx=5)
    
    def handle_drop(self, dragged_label, x, y):
        """处理拖拽释放事件"""
        if not self.grid_window or not self.grid_window.winfo_exists():
            return
        
        # 查找目标网格单元
        target_cell = None
        for row in self.grid_cells:
            for cell in row:
                # 获取单元格在屏幕上的位置
                cell_x = cell.winfo_rootx()
                cell_y = cell.winfo_rooty()
                cell_width = cell.winfo_width()
                cell_height = cell.winfo_height()
                
                # 检查是否在目标单元格上
                if (cell_x <= x <= cell_x + cell_width and 
                    cell_y <= y <= cell_y + cell_height):
                    target_cell = cell
                    break
            if target_cell:
                break
        
        # 如果找到了目标单元格，且不是当前单元格，则交换
        if target_cell and target_cell != dragged_label.original_parent:
            # 找到目标单元格中的标签（如果有的话）
            target_label = None
            for label in self.draggable_labels:
                if label.original_parent == target_cell:
                    target_label = label
                    break
            
            # 交换两个标签的父容器
            dragged_current_parent = dragged_label.original_parent
            if target_label:
                # 两个单元格都有标签，交换它们
                dragged_label.original_parent = target_cell
                target_label.original_parent = dragged_current_parent
                
                # 更新标签的网格位置信息
                dragged_label.grid_row, dragged_label.grid_col = target_cell.row, target_cell.col
                target_label.grid_row, target_label.grid_col = dragged_current_parent.row, dragged_current_parent.col
                
                # 重新放置标签
                dragged_label.place_forget()
                dragged_label.place(relx=0.5, rely=0.5, anchor="center")
                target_label.place_forget()
                target_label.place(relx=0.5, rely=0.5, anchor="center")
                
                # 更新ordered_image_paths
                dragged_index = dragged_current_parent.row * self.cols.get() + dragged_current_parent.col
                target_index = target_cell.row * self.cols.get() + target_cell.col
                self.ordered_image_paths[dragged_index], self.ordered_image_paths[target_index] = \
                    self.ordered_image_paths[target_index], self.ordered_image_paths[dragged_index]
                    
                # 刷新网格界面以反映新的顺序
                self.refresh_grid_display()
            else:
                # 目标单元格是空的，移动标签到目标单元格
                dragged_label.original_parent = target_cell
                dragged_label.grid_row, dragged_label.grid_col = target_cell.row, target_cell.col
                dragged_label.place_forget()
                dragged_label.place(relx=0.5, rely=0.5, anchor="center")
                
                # 更新ordered_image_paths
                old_index = dragged_current_parent.row * self.cols.get() + dragged_current_parent.col
                new_index = target_cell.row * self.cols.get() + target_cell.col
                self.ordered_image_paths[new_index] = self.ordered_image_paths[old_index]
                self.ordered_image_paths[old_index] = None
                
                # 刷新网格界面以反映新的顺序
                self.refresh_grid_display()
        else:
            # 没有找到目标单元格或在原单元格释放，回到原位置
            dragged_label.place_forget()
            dragged_label.place(relx=0.5, rely=0.5, anchor="center")
    
    def refresh_grid_display(self):
        """刷新网格显示以反映当前的图片顺序"""
        if not self.grid_window or not self.grid_window.winfo_exists():
            return
            
        # 清除现有的标签
        for label in self.draggable_labels:
            label.destroy()
        self.draggable_labels = []
        
        # 重新创建标签
        rows = self.rows.get()
        cols = self.cols.get()
        
        for i in range(rows):
            for j in range(cols):
                idx = i * cols + j
                cell_frame = self.grid_cells[i][j]
                
                # 清除单元格中的现有内容
                for widget in cell_frame.winfo_children():
                    widget.destroy()
                
                if idx < len(self.ordered_image_paths) and self.ordered_image_paths[idx]:
                    # 显示图片
                    try:
                        with Image.open(self.ordered_image_paths[idx]) as img:
                            img_copy = img.copy()
                            img_copy.thumbnail((90, 90), Image.Resampling.LANCZOS)
                            photo = ImageTk.PhotoImage(img_copy)
                            
                            # 创建可拖拽的标签而不是普通标签
                            label = DraggableLabel(cell_frame, self.ordered_image_paths[idx], photo, 
                                                 i, j, self, image=photo, bd=0)
                            label.image = photo  # 保持引用
                            label.place(relx=0.5, rely=0.5, anchor="center")
                            self.draggable_labels.append(label)
                    except Exception as e:
                        print(f"加载图片时出错: {e}")
                        placeholder = tk.Label(cell_frame, text="错误", bg="lightgray")
                        placeholder.place(relx=0.5, rely=0.5, anchor="center")
                else:
                    # 显示空位
                    placeholder = tk.Label(cell_frame, text="空", bg="lightgray")
                    placeholder.place(relx=0.5, rely=0.5, anchor="center")
    
    def preview_puzzle(self):
        """预览拼图"""
        # 验证输入
        if not self.image_paths:
            messagebox.showerror("错误", "请先选择图片文件")
            return
        
        rows = self.rows.get()
        cols = self.cols.get()
        
        if rows <= 0 or cols <= 0:
            messagebox.showerror("错误", "行数和列数必须大于0")
            return
        
        try:
            # 使用重新排序的图片路径创建拼图（如果网格布局窗口打开过）
            image_paths_to_use = self.ordered_image_paths if self.ordered_image_paths and len(self.ordered_image_paths) == len(self.image_paths) else self.image_paths
            
            # 创建拼图
            self.puzzle_image = self.create_puzzle(
                image_paths_to_use, 
                rows, 
                cols, 
                self.border.get()
            )
            
            # 创建预览窗口
            self.show_preview_window()
            
        except Exception as e:
            messagebox.showerror("错误", f"创建拼图预览时出错: {str(e)}")
    
    def show_preview_window(self):
        """显示预览窗口"""
        if self.puzzle_image is None:
            return
        
        # 创建预览窗口
        preview_window = tk.Toplevel(self.root)
        preview_window.title("拼图预览")
        preview_window.geometry("800x600")
        
        # 创建滚动区域
        canvas = tk.Canvas(preview_window)
        scrollbar_y = ttk.Scrollbar(preview_window, orient="vertical", command=canvas.yview)
        scrollbar_x = ttk.Scrollbar(preview_window, orient="horizontal", command=canvas.xview)
        scrollable_frame = ttk.Frame(canvas)
        
        canvas.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
        
        # 将拼图调整为适合预览的尺寸
        preview_image = self.puzzle_image.copy()
        max_preview_size = (700, 500)
        preview_image.thumbnail(max_preview_size, Image.Resampling.LANCZOS)
        
        # 创建PhotoImage
        self.puzzle_photo = ImageTk.PhotoImage(preview_image)
        
        # 在滚动区域中显示图片
        canvas.create_image(0, 0, anchor="nw", image=self.puzzle_photo)
        canvas.configure(scrollregion=canvas.bbox("all"))
        
        # 布局
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar_y.pack(side="right", fill="y")
        scrollbar_x.pack(side="bottom", fill="x")
        
        # 保存按钮
        save_button = ttk.Button(preview_window, text="保存拼图", command=lambda: self.save_puzzle(preview_window))
        save_button.pack(side="bottom", pady=10)
    
    def save_puzzle(self, preview_window=None):
        """保存拼图"""
        if self.puzzle_image is None:
            messagebox.showerror("错误", "请先生成拼图预览")
            return
        
        # 如果没有设置输出文件，弹出文件选择对话框
        if not self.output_file.get():
            file = filedialog.asksaveasfilename(
                defaultextension=".jpg",
                filetypes=[("JPEG files", "*.jpg"), ("PNG files", "*.png"), ("All files", "*.*")]
            )
            if file:
                self.output_file.set(file)
            else:
                return
        
        try:
            # 保存拼图
            self.puzzle_image.save(self.output_file.get())
            messagebox.showinfo("成功", f"拼图已保存到: {self.output_file.get()}")
            
            # 关闭预览窗口（如果存在）
            if preview_window:
                preview_window.destroy()
                
        except Exception as e:
            messagebox.showerror("错误", f"保存拼图时出错: {str(e)}")
    
    def generate_puzzle(self):
        """生成拼图并预览"""
        self.preview_puzzle()
    
    def create_widgets(self):
        """创建界面控件"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # 输入图片选择
        ttk.Label(main_frame, text="图片文件:").grid(row=0, column=0, sticky=tk.W, pady=5)
        image_frame = ttk.Frame(main_frame)
        image_frame.grid(row=0, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        image_frame.columnconfigure(0, weight=1)
        
        ttk.Button(image_frame, text="添加图片...", command=self.browse_images).grid(row=0, column=0, padx=(0, 5))
        ttk.Label(image_frame, text="（可多次添加图片）").grid(row=0, column=1, sticky=tk.W)
        
        # 输出文件选择
        ttk.Label(main_frame, text="输出文件:").grid(row=1, column=0, sticky=tk.W, pady=5)
        output_frame = ttk.Frame(main_frame)
        output_frame.grid(row=1, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        output_frame.columnconfigure(0, weight=1)
        
        ttk.Entry(output_frame, textvariable=self.output_file).grid(
            row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5)
        )
        ttk.Button(output_frame, text="浏览...", command=self.browse_output).grid(row=0, column=1)
        
        # 参数设置
        params_frame = ttk.LabelFrame(main_frame, text="拼图参数", padding="10")
        params_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        params_frame.columnconfigure(1, weight=1)
        params_frame.columnconfigure(3, weight=1)
        params_frame.columnconfigure(5, weight=1)
        
        ttk.Label(params_frame, text="行数:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        ttk.Spinbox(params_frame, from_=1, to=20, textvariable=self.rows, width=10).grid(
            row=0, column=1, sticky=tk.W, padx=(0, 10)
        )
        
        ttk.Label(params_frame, text="列数:").grid(row=0, column=2, sticky=tk.W, padx=(0, 5))
        ttk.Spinbox(params_frame, from_=1, to=20, textvariable=self.cols, width=10).grid(
            row=0, column=3, sticky=tk.W, padx=(0, 10)
        )
        
        ttk.Label(params_frame, text="白边宽度:").grid(row=0, column=4, sticky=tk.W, padx=(0, 5))
        ttk.Spinbox(params_frame, from_=0, to=50, textvariable=self.border, width=10).grid(
            row=0, column=5, sticky=tk.W
        )
        
        ttk.Label(params_frame, text="调整模式:").grid(row=1, column=0, sticky=tk.W, pady=(10, 0))
        resize_mode_frame = ttk.Frame(params_frame)
        resize_mode_frame.grid(row=1, column=1, columnspan=2, sticky=tk.W, pady=(10, 0))
        
        ttk.Radiobutton(resize_mode_frame, text="缩放", variable=self.resize_mode, value="scale").pack(side=tk.LEFT)
        ttk.Radiobutton(resize_mode_frame, text="裁剪", variable=self.resize_mode, value="crop").pack(side=tk.LEFT)
        
        # 保持纵横比选项
        ttk.Checkbutton(params_frame, text="保持图片纵横比", variable=self.keep_aspect_ratio).grid(
            row=1, column=3, columnspan=2, sticky=tk.W, pady=(10, 0)
        )
        
        # 网格信息显示
        self.grid_info_label = ttk.Label(params_frame, text="")
        self.grid_info_label.grid(row=2, column=0, columnspan=6, sticky=tk.W, pady=(10, 0))
        
        # 图片数量显示和推荐按钮
        count_frame = ttk.Frame(main_frame)
        count_frame.grid(row=3, column=0, columnspan=3, sticky=tk.W, pady=5)
        
        self.image_count_label = ttk.Label(count_frame, text="未选择图片")
        self.image_count_label.pack(side=tk.LEFT)
        
        ttk.Button(count_frame, text="推荐行列数", command=self.recommend_grid).pack(side=tk.LEFT, padx=(10, 5))
        ttk.Button(count_frame, text="网格布局", command=self.show_grid_layout).pack(side=tk.LEFT)
        
        # 图片预览区域
        ttk.Label(main_frame, text="图片预览:").grid(row=4, column=0, sticky=tk.W, pady=(10, 5))
        
        self.preview_frame = ttk.Frame(main_frame)
        self.preview_frame.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        main_frame.rowconfigure(5, weight=1)
        self.preview_frame.columnconfigure(0, weight=1)
        self.preview_frame.rowconfigure(0, weight=1)
        
        # 按钮区域
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=6, column=0, columnspan=3, pady=10)
        
        # 生成并预览按钮
        ttk.Button(button_frame, text="生成并预览拼图", command=self.generate_puzzle).pack(side=tk.LEFT, padx=(0, 10))
        
        # 直接保存按钮
        ttk.Button(button_frame, text="直接保存", command=lambda: self.save_puzzle()).pack(side=tk.LEFT)

def main():
    root = tk.Tk()
    app = PuzzleApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()