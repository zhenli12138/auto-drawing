import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import cv2
import keyboard
import numpy as np
import pyautogui
from PIL import Image, ImageTk

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
        self.root.title("AutoDraw Assistant")

        self.original_image = None
        self.line_image = None
        self.selected_area = None
        self.drawing = False
        self.stop_flag = False

        self.create_widgets()
        self.setup_hotkeys()
        self.min_line_length = 15  # 最小线条长度
    # 页面设置
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
        self.speed_scale = ttk.Scale(params_frame, from_=0.1, to=5, value=1)
        self.speed_scale.pack(side=tk.LEFT, padx=5)

        ttk.Label(params_frame, text="绘制精度:").pack(side=tk.LEFT)
        self.precision_scale = ttk.Scale(params_frame, from_=1, to=10, value=5)
        self.precision_scale.pack(side=tk.LEFT, padx=5)

        # 图像显示
        image_frame = ttk.Frame(main_frame)
        image_frame.pack(fill=tk.BOTH, expand=True)

        self.original_label = ttk.Label(image_frame)
        self.original_label.pack(side=tk.LEFT, padx=5, pady=5)

        self.line_label = ttk.Label(image_frame)
        self.line_label.pack(side=tk.LEFT, padx=5, pady=5)

    # 设置热键
    def setup_hotkeys(self):
        keyboard.add_hotkey('space', self.stop_drawing)

    # 加载图片
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

    # 转换为线条图
    def convert_to_line_art(self, file_path):
        try:
            img = cv2.imread(file_path)
            #转灰度图
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            #高斯模糊去噪声
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            #边缘检测
            edges = cv2.Canny(blurred, 30, 100)
            kernel = np.ones((2, 2), np.uint8)
            # 膨胀操作，使线条更连续
            edges = cv2.dilate(edges, kernel, iterations=1)
            #将边缘检测结果（edges）转换为PIL灰度图像
            self.line_image = Image.fromarray(edges).convert("L")
            #调用图像显示函数
            self.show_image(self.line_image, self.line_label)
        except Exception as e:
            messagebox.showerror("错误", f"线条转换失败: {str(e)}")

    #预览图片
    def show_image(self, image, label):
        w, h = image.size
        ratio = min(400 / w, 400 / h)
        new_size = (int(w * ratio), int(h * ratio))
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
        self.drawing = True
        try:
            img = self.process_line_image()
            contours = self.get_contours(img)
            self.draw_contours(contours)
        except Exception as e:
            messagebox.showerror("错误", f"绘制失败: {str(e)}")
        finally:
            self.drawing = False

    def process_line_image(self):
        img = self.line_image.resize((
            self.selected_area[2],
            self.selected_area[3]
        ))
        return np.array(img)

    def get_contours(self, img):
        contours, _ = cv2.findContours(
            img, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE
        )
        # 过滤小轮廓
        contours = [c for c in contours if cv2.contourArea(c) > self.min_line_length]
        return sorted(contours, key=cv2.contourArea, reverse=True)

    def draw_contours(self, contours):
        #绘图起始(base_x, base_y) 位置
        base_x = self.selected_area[0]
        base_y = self.selected_area[1]

        #将鼠标移动到指定的 (base_x, base_y) 位置，并释放鼠标按键。
        pyautogui.moveTo(base_x, base_y)
        pyautogui.mouseUp()

        #从 GUI 控件中获取的值，分别用于控制鼠标移动的精度和速度
        precision = int(self.precision_scale.get())
        speed = self.speed_scale.get()

        #绘图循环
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