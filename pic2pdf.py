import os
import re
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import math
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
import io

class ImageToPDFConverter:
    def __init__(self, root):
        self.root = root
        self.root.title("图片转PDF工具")
        self.root.geometry("800x600")
        
        self.image_folder = tk.StringVar()
        self.output_file = tk.StringVar()
        self.image_paths = []
        self.preview_images = []
        
        self.create_widgets()
        
    def create_widgets(self):
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(3, weight=1)
        
        # 输入文件夹选择
        ttk.Label(main_frame, text="图片文件夹:").grid(row=0, column=0, sticky=tk.W, pady=5)
        folder_frame = ttk.Frame(main_frame)
        folder_frame.grid(row=0, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        folder_frame.columnconfigure(0, weight=1)
        
        ttk.Entry(folder_frame, textvariable=self.image_folder, state="readonly").grid(
            row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5)
        )
        ttk.Button(folder_frame, text="浏览...", command=self.browse_folder).grid(row=0, column=1)
        
        # 输出文件选择
        ttk.Label(main_frame, text="输出PDF文件:").grid(row=1, column=0, sticky=tk.W, pady=5)
        output_frame = ttk.Frame(main_frame)
        output_frame.grid(row=1, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        output_frame.columnconfigure(0, weight=1)
        
        ttk.Entry(output_frame, textvariable=self.output_file).grid(
            row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5)
        )
        ttk.Button(output_frame, text="浏览...", command=self.browse_output).grid(row=0, column=1)
        
        # 图片数量显示
        self.image_count_label = ttk.Label(main_frame, text="未选择文件夹")
        self.image_count_label.grid(row=2, column=0, columnspan=3, sticky=tk.W, pady=5)
        
        # 图片预览区域
        ttk.Label(main_frame, text="图片预览:").grid(row=3, column=0, sticky=tk.W, pady=(10, 5))
        
        self.preview_frame = ttk.Frame(main_frame)
        self.preview_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        self.preview_frame.columnconfigure(0, weight=1)
        self.preview_frame.rowconfigure(0, weight=1)
        
        # 按钮区域
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, columnspan=3, pady=10)
        
        self.convert_button = ttk.Button(button_frame, text="转换为PDF", command=self.convert_to_pdf, state="disabled")
        self.convert_button.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(button_frame, text="退出", command=self.root.quit).pack(side=tk.LEFT)
    
    def natural_sort_key(self, text):
        """自然排序键函数"""
        return [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', text)]
    
    def get_image_files(self, folder_path):
        """获取文件夹中的所有图片文件并按名称排序"""
        supported_formats = ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff')
        files = [f for f in os.listdir(folder_path) if f.lower().endswith(supported_formats)]
        files.sort(key=self.natural_sort_key)
        return [os.path.join(folder_path, f) for f in files]
    
    def browse_folder(self):
        """选择图片文件夹"""
        folder = filedialog.askdirectory()
        if folder:
            self.image_folder.set(folder)
            self.load_images()
    
    def browse_output(self):
        """选择输出PDF文件"""
        file = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        if file:
            self.output_file.set(file)
    
    def load_images(self):
        """加载并预览图片"""
        folder = self.image_folder.get()
        if not folder or not os.path.exists(folder):
            return
        
        self.image_paths = self.get_image_files(folder)
        
        # 清空之前的预览
        for widget in self.preview_frame.winfo_children():
            widget.destroy()
        
        self.preview_images = []
        
        # 显示图片预览
        if self.image_paths:
            # 创建一个滚动区域来显示预览图
            canvas = tk.Canvas(self.preview_frame)
            scrollbar = ttk.Scrollbar(self.preview_frame, orient="vertical", command=canvas.yview)
            scrollable_frame = ttk.Frame(canvas)
            
            scrollable_frame.bind(
                "<Configure>",
                lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
            )
            
            canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)
            
            # 显示图片
            for i, path in enumerate(self.image_paths):
                try:
                    with Image.open(path) as img:
                        # 创建缩略图
                        img_copy = img.copy()
                        img_copy.thumbnail((150, 150), Image.Resampling.LANCZOS)
                        photo = ImageTk.PhotoImage(img_copy)
                        self.preview_images.append(photo)  # 保持引用
                        
                        # 创建预览标签
                        frame = ttk.Frame(scrollable_frame)
                        frame.grid(row=i//5, column=i%5, padx=5, pady=5)
                        
                        label = ttk.Label(frame, image=photo)
                        label.pack()
                        
                        name_label = ttk.Label(frame, text=os.path.basename(path), 
                                              wraplength=150, justify="center")
                        name_label.pack()
                except Exception as e:
                    print(f"加载预览图 {path} 时出错: {e}")
            
            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            
            # 更新图片数量显示
            self.image_count_label.config(text=f"找到 {len(self.image_paths)} 张图片")
            
            # 启用转换按钮
            self.convert_button.config(state="normal")
            
            # 如果没有设置输出文件，自动生成一个
            if not self.output_file.get():
                folder_name = os.path.basename(folder)
                self.output_file.set(os.path.join(folder, f"{folder_name}.pdf"))
        else:
            # 没有图片时显示提示
            no_image_label = ttk.Label(self.preview_frame, text="该文件夹中没有找到支持的图片文件")
            no_image_label.pack(expand=True)
            self.image_count_label.config(text="未找到图片文件")
            self.convert_button.config(state="disabled")
    
    def resize_image_for_a4_portrait(self, img):
        """
        将图片调整为适合纵向A4纸的尺寸
        返回调整后的图片和是否需要旋转的标志
        """
        # A4尺寸 (宽, 高) in points (1 point = 1/72 inch)
        a4_width, a4_height = A4  # (595.276, 841.890)
        
        # 获取原始图片尺寸
        img_width, img_height = img.size
        
        # 计算两种方案的缩放比例：
        # 方案1：直接放置在纵向A4上
        direct_width_ratio = a4_width / img_width
        direct_height_ratio = a4_height / img_height
        direct_scale_ratio = min(direct_width_ratio, direct_height_ratio)
        
        # 方案2：旋转90度后放置在纵向A4上
        rotated_width_ratio = a4_width / img_height
        rotated_height_ratio = a4_height / img_width
        rotated_scale_ratio = min(rotated_width_ratio, rotated_height_ratio)
        
        # 选择能获得更大图片的方案
        if rotated_scale_ratio > direct_scale_ratio:
            # 旋转图片
            should_rotate = True
            scale_ratio = rotated_scale_ratio
            # 旋转图片90度
            img = img.rotate(90, expand=True)
            # 更新尺寸
            img_width, img_height = img_height, img_width
        else:
            # 不旋转图片
            should_rotate = False
            scale_ratio = direct_scale_ratio
        
        # 如果图片比A4小，则不放大
        if scale_ratio > 1:
            scale_ratio = 1
            
        # 计算新尺寸
        new_width = int(img_width * scale_ratio)
        new_height = int(img_height * scale_ratio)
        
        # 调整图片尺寸
        resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        return resized_img, should_rotate
    
    def convert_to_pdf(self):
        """将图片转换为PDF，所有页面都是纵向A4"""
        # 验证输入
        if not self.image_folder.get():
            messagebox.showerror("错误", "请选择图片文件夹")
            return
        
        if not self.image_paths:
            messagebox.showerror("错误", "未找到图片文件")
            return
        
        # 如果没有设置输出文件，弹出文件选择对话框
        if not self.output_file.get():
            file = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
            )
            if file:
                self.output_file.set(file)
            else:
                return
        
        try:
            # 创建PDF文件，所有页面都是纵向A4
            output_path = self.output_file.get()
            c = canvas.Canvas(output_path, pagesize=A4)
            a4_width, a4_height = A4
            
            # 处理每张图片
            for i, img_path in enumerate(self.image_paths):
                try:
                    # 打开图片
                    with Image.open(img_path) as img:
                        # 转换为RGB模式（如果需要）
                        if img.mode in ('RGBA', 'LA', 'P'):
                            # 创建白色背景
                            rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                            if img.mode == 'P':
                                img = img.convert('RGBA')
                            rgb_img.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                            img = rgb_img
                        
                        # 调整图片尺寸以适应纵向A4，并决定是否旋转
                        resized_img, was_rotated = self.resize_image_for_a4_portrait(img)
                        
                        # 确保页面是纵向A4（可能前面的页面改变了页面尺寸）
                        c.setPageSize(A4)
                        
                        # 计算居中位置
                        img_width, img_height = resized_img.size
                        x = (a4_width - img_width) / 2
                        y = (a4_height - img_height) / 2
                        
                        # 将PIL图片转换为BytesIO
                        img_buffer = io.BytesIO()
                        resized_img.save(img_buffer, format='JPEG', quality=95)
                        img_buffer.seek(0)
                        
                        # 在PDF中绘制图片
                        c.drawImage(ImageReader(img_buffer), x, y, width=img_width, height=img_height)
                        
                        # 添加新页面（除了最后一张图片）
                        if i < len(self.image_paths) - 1:
                            c.showPage()
                
                except Exception as e:
                    print(f"处理图片 {img_path} 时出错: {e}")
                    # 即使某张图片出错，也继续处理其他图片
                    if i < len(self.image_paths) - 1:
                        c.showPage()
            
            # 保存PDF
            c.save()
            
            messagebox.showinfo("成功", f"PDF文件已保存到: {output_path}\n所有页面均为纵向A4格式")
            
        except Exception as e:
            messagebox.showerror("错误", f"转换PDF时出错: {str(e)}")

def main():
    root = tk.Tk()
    app = ImageToPDFConverter(root)
    root.mainloop()

if __name__ == "__main__":
    # 检查是否安装了必要的库
    try:
        import reportlab
        main()
    except ImportError:
        print("缺少必要的库，请安装:")
        print("pip install reportlab pillow")
        input("按回车键退出...")