import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import cv2
import numpy as np
import pyautogui
import threading
import keyboard
from PIL import Image, ImageTk, ImageDraw, ImageOps
pyautogui.PAUSE = 0.01


class AreaSelector:
    def __init__(self, line_image, callback):
        self.line_image = line_image
        self.callback = callback
        self.start_x = None
        self.start_y = None
        self.current_x = None
        self.current_y = None

        self.overlay = tk.Toplevel()
        self.overlay.attributes("-fullscreen", True)
        self.overlay.attributes("-alpha", 0.3)
        self.overlay.attributes("-topmost", True)
        self.canvas = tk.Canvas(self.overlay, cursor="cross")
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)

    def on_press(self, event):
        self.start_x = event.x
        self.start_y = event.y
        self.rect = self.canvas.create_rectangle(
            self.start_x, self.start_y,
            self.start_x, self.start_y,
            outline="red", width=2
        )

    def on_drag(self, event):
        self.current_x, self.current_y = event.x, event.y
        self.canvas.coords(
            self.rect,
            self.start_x, self.start_y,
            self.current_x, self.current_y
        )
        self.draw_preview()

    def draw_preview(self):
        preview = self.line_image.copy()
        preview = preview.resize((
            abs(self.current_x - self.start_x),
            abs(self.current_y - self.start_y)
        ))

        preview_window = tk.Toplevel()
        preview_window.overrideredirect(1)
        preview_window.geometry(f"+{self.start_x}+{self.start_y}")
        preview_label = ttk.Label(preview_window)
        preview_label.pack()

        photo = ImageTk.PhotoImage(preview)
        preview_label.config(image=photo)
        preview_label.image = photo
        preview_window.after(100, preview_window.destroy)

    def on_release(self, event):
        screen_width = self.overlay.winfo_screenwidth()
        screen_height = self.overlay.winfo_screenheight()

        selected_area = (
            min(self.start_x, self.current_x) / screen_width,
            min(self.start_y, self.current_y) / screen_height,
            abs(self.current_x - self.start_x) / screen_width,
            abs(self.current_y - self.start_y) / screen_height
        )
        self.overlay.destroy()
        self.callback(selected_area)


class AutoDrawingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AutoDraw自动绘图（达莉娅制）")

        self.original_image = None
        self.line_image = None
        self.selected_area = None
        self.drawing = False
        self.stop_flag = False

        self.create_widgets()
        self.setup_hotkeys()
        self.min_line_length = 5  # 最小线条长度
    def create_widgets(self):
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 控制面板
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Button(control_frame, text="上传图片", command=self.load_image).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="选择区域", command=self.start_area_selection).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="重置区域", command=self.reset_area).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="开始绘制", command=self.start_drawing).pack(side=tk.LEFT, padx=5)

        # 参数设置
        params_frame = ttk.Frame(main_frame)
        params_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(params_frame, text="绘制速度:").pack(side=tk.LEFT)
        self.speed_scale = ttk.Scale(params_frame, from_=1, to=10, value=1)
        self.speed_scale.pack(side=tk.LEFT, padx=5)
        self.speed_value_label = ttk.Label(params_frame, text="1")
        self.speed_value_label.pack(side=tk.LEFT)
        # 绑定滑块值变化事件
        self.speed_scale.configure(command=lambda v: self.speed_value_label.config(text=f"{float(v):.3f}"))

        ttk.Label(params_frame, text="绘制精度:").pack(side=tk.LEFT)
        self.precision_scale = ttk.Scale(params_frame, from_=1, to=2, value=1)
        self.precision_scale.pack(side=tk.LEFT, padx=5)
        self.precision_value_label = ttk.Label(params_frame, text="1")
        self.precision_value_label.pack(side=tk.LEFT)
        # 绑定滑块值变化事件
        self.precision_scale.configure(command=lambda v: self.precision_value_label.config(text=f"{float(v):.3f}"))
        # 图像显示
        image_frame = ttk.Frame(main_frame)
        image_frame.pack(fill=tk.BOTH, expand=True)

        self.original_label = ttk.Label(image_frame)
        self.original_label.pack(side=tk.LEFT, padx=5, pady=5)

        self.line_label = ttk.Label(image_frame)
        self.line_label.pack(side=tk.LEFT, padx=5, pady=5)

    def setup_hotkeys(self):
        keyboard.add_hotkey('space', self.stop_drawing)

    def load_image(self):
        file_path = filedialog.askopenfilename(filetypes=[("Image files", "*.jpg *.jpeg *.png")])
        if not file_path:
            return

        try:
            self.original_image = Image.open(file_path)
            self.show_image(self.original_image, self.original_label)
            self.convert_to_line_art(file_path)
        except Exception as e:
            messagebox.showerror("错误", f"图片加载失败: {str(e)}")

    def convert_to_line_art(self, file_path):
        try:
            img = cv2.imread(file_path)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            edges = cv2.Canny(blurred, 55, 100)
            kernel = np.ones((2, 2), np.uint8)
            edges = cv2.dilate(edges, kernel, iterations=1)
            self.line_image = Image.fromarray(edges).convert("L")
            self.show_image(self.line_image, self.line_label)
        except Exception as e:
            messagebox.showerror("错误", f"线条转换失败: {str(e)}")

    def show_image(self, image, label):
        w, h = image.size
        ratio = min(400 / w, 400 / h)
        new_size = (int(w*ratio), int(h*ratio))
        resized = image.resize(new_size)

        photo = ImageTk.PhotoImage(resized)
        label.config(image=photo)
        label.image = photo

    def start_area_selection(self):
        if self.line_image is None:
            messagebox.showwarning("警告", "请先上传并转换图片")
            return

        self.root.iconify()
        threading.Thread(target=self.run_area_selector).start()

    def run_area_selector(self):
        selector = AreaSelector(self.line_image, self.save_selected_area)

    def save_selected_area(self, normalized_area):
        self.root.deiconify()
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()

        self.selected_area = (
            int(normalized_area[0] * screen_w),
            int(normalized_area[1] * screen_h),
            int(normalized_area[2] * screen_w),
            int(normalized_area[3] * screen_h)
        )
        messagebox.showinfo("区域已选择",
                            f"选择区域: X:{self.selected_area[0]} Y:{self.selected_area[1]}\n"
                            f"宽高: {self.selected_area[2]}x{self.selected_area[3]}")

    def reset_area(self):
        self.selected_area = None

    def start_drawing(self):
        if not self.selected_area:
            messagebox.showwarning("警告", "请先选择绘制区域")
            return

        if self.drawing:
            return

        self.stop_flag = False
        threading.Thread(target=self.draw_operation).start()

    def draw_operation(self):
        # 标记绘制状态为进行中
        self.drawing = True
        try:
            # 1. 处理线条图：将线条图缩放到用户选择的区域尺寸
            img = self.process_line_image()
            # 2. 获取轮廓：从处理后的图像中提取绘制路径
            contours = self.get_contours(img)
            # 3. 绘制轮廓：按照提取的路径模拟鼠标绘制
            self.draw_contours(contours)
        except Exception as e:
            # 捕获并显示任何异常
            messagebox.showerror("错误", f"绘制失败: {str(e)}")
        finally:
            # 无论成功或失败，最终都将绘制状态标记为结束
            self.drawing = False

    def process_line_image(self):
        # 将线条图缩放到用户选择的区域尺寸
        img = self.line_image.resize((
            self.selected_area[2],  # 用户选择区域的宽度
            self.selected_area[3]  # 用户选择区域的高度
        ))
        # 将 PIL Image 转换为 NumPy 数组（OpenCV 兼容格式）
        return np.array(img)

    def get_contours(self, img):
        contours, _ = cv2.findContours(
            img, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE
        )

        # 计算每个轮廓的垂直位置（使用包围盒顶部坐标）
        def get_vertical_position(c):
            _, y, _, _ = cv2.boundingRect(c)
            return y

        # 按垂直位置排序，相同高度时按水平位置排序
        contours = sorted(contours,
                          key=lambda c: (get_vertical_position(c), cv2.boundingRect(c)[0]))
        return contours

    def draw_contours(self, contours):
        base_x = self.selected_area[0]
        base_y = self.selected_area[1]

        pyautogui.moveTo(base_x, base_y)
        pyautogui.mouseUp()

        precision = int(self.precision_scale.get())
        speed = self.speed_scale.get()

        for contour in contours:
            if self.stop_flag:
                break

            points = contour[::precision]
            if len(points) < 2:
                continue

            start_x = base_x + int(points[0][0][0])
            start_y = base_y + int(points[0][0][1])

            pyautogui.moveTo(start_x, start_y, duration=0.1 / speed)
            pyautogui.mouseDown()

            for point in points[1:]:
                if self.stop_flag:
                    break
                x = base_x + int(point[0][0])
                y = base_y + int(point[0][1])
                pyautogui.moveTo(x, y, duration=0.05 / speed)

            pyautogui.mouseUp()

    def stop_drawing(self):
        self.stop_flag = True
        pyautogui.mouseUp()


if __name__ == "__main__":
    root = tk.Tk()
    app = AutoDrawingApp(root)
    root.mainloop()