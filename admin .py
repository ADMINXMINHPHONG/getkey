import argparse
import requests
import json
import uuid
import datetime
import time
from urllib.parse import quote_plus

import tkinter as tk
from tkinter import ttk, messagebox, font
import threading

# --- CẤU HÌNH ---
FIREBASE_CONFIG = {
    'projectId': 'honghac-builda-keys',
    'apiKey': 'AIzaSyCsR_yDVQGgeqJAp5NvLWeLkPgz0scN-Xw',
    'databaseURL': 'https://honghac-builda-keys-default-rtdb.asia-southeast1.firebasedatabase.app'
}
FIRESTORE_BASE = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_CONFIG['projectId']}/databases/(default)/documents"

SHORTENER_API = {
    "url": "https://linkx.me/st",
    "key": "6dcebdb087455c5593512aa5be6e7d86894c3de0"
}

KEY_PAGE_URL = "https://modgame08.top/key.html?key="

# --- HÀM HỖ TRỢ ---

def get_steplink1(full_url, timeout=15):
    """Truy cập link rút gọn và lấy URL đích sau khi chuyển hướng."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    try:
        response = requests.get(full_url, headers=headers, allow_redirects=True, timeout=timeout)
        return response.url
    except Exception as e:
        print(f"Lỗi khi lấy redirect: {e}")
        return None

def save_to_firestore(key_id, short_link, steplink1=None, expires_seconds=None):
    """Lưu thông tin key và short link vào Firestore."""
    data_fields = {
        "key": {"stringValue": key_id},
        "created": {"integerValue": str(int(time.time()))},
        "short_link": {"stringValue": short_link},
        "used": {"booleanValue": False}
    }
    if steplink1:
        data_fields["steplink1"] = {"stringValue": steplink1}
    
    if expires_seconds:
        data_fields["expires_seconds"] = {"integerValue": str(expires_seconds)}

    try:
        # Write to /keys/{key_id}
        requests.patch(f"{FIRESTORE_BASE}/keys/{key_id}", json={"fields": data_fields}, params={"key": FIREBASE_CONFIG['apiKey']})
        
        # Also write shortlinks collection so frontend can pick it (ready=true)
        short_data = {"fields": {"short_link": {"stringValue": short_link}, "ready": {"booleanValue": True}}}
        if steplink1:
            short_data["fields"]["steplink1"] = {"stringValue": steplink1}
            
        requests.patch(f"{FIRESTORE_BASE}/shortlinks/{key_id}", json=short_data, params={"key": FIREBASE_CONFIG['apiKey']})
        return True
    except Exception as e:
        print(f"Lỗi lưu Firestore: {e}")
        return False

# --- LOGIC TẠO KEY ---
def generate_keys_logic(count, prefix, use_quote, auto_resolve, expires_seconds, callback_progress=None):
    short_links = []
    
    for i in range(count):
        key_id = f"{prefix}{uuid.uuid4().hex[:8].upper()}"
        target = f"{KEY_PAGE_URL}{key_id}"
        
        if use_quote:
            wrapped = f"{SHORTENER_API['url']}?api={SHORTENER_API['key']}&url={quote_plus(target)}"
        else:
            wrapped = f"{SHORTENER_API['url']}?api={SHORTENER_API['key']}&url={target}"

        steplink1 = None
        if auto_resolve:
            steplink1 = get_steplink1(wrapped)

        save_to_firestore(key_id, wrapped, steplink1=steplink1, expires_seconds=expires_seconds)
        short_links.append(wrapped)
        
        if callback_progress:
            callback_progress(i + 1, count, wrapped)

        time.sleep(0.5)

    try:
        with open('short.txt', 'w', encoding='utf-8') as f:
            for s in short_links:
                f.write(s + '\n')
    except Exception: pass

    return short_links

# --- GUI ADMIN ---
class AdminGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("HongHac Admin - Quản Lý Key")
        self.root.geometry("1000x650")
        
        self.style = ttk.Style()
        try:
            self.style.theme_use('clam')
        except: pass
        
        default_font = font.nametofont("TkDefaultFont")
        default_font.configure(family="Segoe UI", size=10)
        
        self.style.configure("Treeview", rowheight=28, font=('Segoe UI', 10))
        self.style.configure("Treeview.Heading", font=('Segoe UI', 10, 'bold'))
        self.style.map("Treeview", background=[('selected', '#0078D7')])

        # --- LAYOUT ---
        header_frame = ttk.Frame(root, padding="10 10 10 5")
        header_frame.pack(fill="x")
        ttk.Label(header_frame, text="HỆ THỐNG TẠO KEY TỰ ĐỘNG", font=("Segoe UI", 16, "bold"), foreground="#2c3e50").pack()

        control_frame = ttk.LabelFrame(root, text="Cấu hình & Thao tác", padding="15 10")
        control_frame.pack(fill="x", padx=15, pady=5)

        input_grid = ttk.Frame(control_frame)
        input_grid.pack(fill="x", pady=(0, 10))

        # --- CẬP NHẬT: SỐ LƯỢNG MẶC ĐỊNH ---
        ttk.Label(input_grid, text="Số lượng:").grid(row=0, column=0, sticky="w", padx=(0,5))
        self.count_var = tk.IntVar(value=1)
        ttk.Spinbox(input_grid, from_=1, to=1000, textvariable=self.count_var, width=8).grid(row=0, column=1, padx=(0, 20))

        # --- CẬP NHẬT: THỜI GIAN MẶC ĐỊNH LÀ 300 ---
        ttk.Label(input_grid, text="Hết hạn (giây):").grid(row=0, column=2, sticky="w", padx=(0,5))
        self.time_var = tk.IntVar(value=300) 
        ttk.Entry(input_grid, textvariable=self.time_var, width=12).grid(row=0, column=3, padx=(0, 20))

        ttk.Label(input_grid, text="Tiền tố:").grid(row=0, column=4, sticky="w", padx=(0,5))
        self.prefix_var = tk.StringVar(value='HH_')
        ttk.Entry(input_grid, textvariable=self.prefix_var, width=15).grid(row=0, column=5, padx=(0, 20))

        self.auto_resolve_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(input_grid, text="Auto Resolve", variable=self.auto_resolve_var).grid(row=0, column=6, padx=(0, 10))

        self.quote_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(input_grid, text="URL Encode", variable=self.quote_var).grid(row=0, column=7)

        ttk.Separator(control_frame, orient='horizontal').pack(fill='x', pady=10)

        btn_grid = ttk.Frame(control_frame)
        btn_grid.pack(fill="x")

        self.create_btn = ttk.Button(btn_grid, text="⚡ TẠO KEY NGAY", command=self.on_create, width=20)
        self.create_btn.pack(side="left", padx=(0, 10))

        self.export_btn = ttk.Button(btn_grid, text="💾 Xuất short.txt", command=self.on_export)
        self.export_btn.pack(side="left", padx=(0, 10))
        
        ttk.Button(btn_grid, text="🔄 Làm mới DS", command=self.refresh).pack(side="right")
        ttk.Button(btn_grid, text="🗑 Xóa đã chọn", command=self.on_delete).pack(side="right", padx=(0, 10))

        data_frame = ttk.LabelFrame(root, text="Danh sách Key trên Cloud", padding="10")
        data_frame.pack(fill="both", expand=True, padx=15, pady=5)

        cols = ("key", "short_link", "steplink1", "created")
        self.tree = ttk.Treeview(data_frame, columns=cols, show='headings', selectmode="extended")
        
        self.tree.column("key", width=150, anchor='w')
        self.tree.column("short_link", width=250, anchor='w')
        self.tree.column("steplink1", width=300, anchor='w')
        self.tree.column("created", width=120, anchor='center')

        self.tree.heading("key", text="MÃ KEY")
        self.tree.heading("short_link", text="LINK RÚT GỌN")
        self.tree.heading("steplink1", text="LINK GỐC")
        self.tree.heading("created", text="NGÀY TẠO")

        scrollbar = ttk.Scrollbar(data_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        self.tree.tag_configure('odd', background='#f9f9f9')
        self.tree.tag_configure('even', background='#ffffff')

        status_frame = ttk.Frame(root, relief="sunken", padding="5")
        status_frame.pack(fill="x", side="bottom")
        self.status = ttk.Label(status_frame, text="Sẵn sàng", anchor='w', font=("Segoe UI", 9))
        self.status.pack(fill="x")

        self.refresh()

    def set_status(self, text):
        self.status.config(text=f" ➤ {text}")

    def refresh(self):
        self.set_status("Đang tải dữ liệu...")
        threading.Thread(target=self._refresh_thread, daemon=True).start()

    def _refresh_thread(self):
        try:
            r = requests.get(f"{FIRESTORE_BASE}/keys", params={"key": FIREBASE_CONFIG['apiKey']}, timeout=10)
            items = []
            if r.status_code == 200:
                docs = r.json().get('documents', [])
                for d in docs:
                    f = d.get('fields', {})
                    items.append({
                        'key': f.get('key', {}).get('stringValue','N/A'),
                        'short_link': f.get('short_link', {}).get('stringValue',''),
                        'steplink1': f.get('steplink1', {}).get('stringValue',''),
                        'created': int(f.get('created', {}).get('integerValue', '0'))
                    })
                items.sort(key=lambda x: x['created'], reverse=True)
                self.root.after(0, self._update_tree_ui, items)
            else:
                self.root.after(0, self.set_status, f"Lỗi server: {r.status_code}")
        except Exception as e:
            self.root.after(0, self.set_status, f"Lỗi kết nối: {e}")

    def _update_tree_ui(self, items):
        self.tree.delete(*self.tree.get_children())
        for index, it in enumerate(items):
            created_ts = it['created']
            created_str = datetime.datetime.fromtimestamp(created_ts).strftime('%Y-%m-%d %H:%M') if created_ts else ''
            tag = 'odd' if index % 2 == 0 else 'even'
            self.tree.insert('', 'end', values=(it['key'], it['short_link'], it['steplink1'], created_str), tags=(tag,))
        self.set_status(f"Đã tải xong {len(items)} key.")

    def on_delete(self):
        sel = self.tree.selection()
        if not sel: return
        key_list = [self.tree.item(i)['values'][0] for i in sel]
        if not messagebox.askyesno('Xác nhận', f'Xóa {len(key_list)} key?'): return
        
        self.set_status(f"Đang xóa {len(key_list)} key...")
        threading.Thread(target=self._delete_thread, args=(key_list,), daemon=True).start()

    def _delete_thread(self, key_list):
        for key in key_list:
            try:
                requests.delete(f"{FIRESTORE_BASE}/keys/{key}", params={"key": FIREBASE_CONFIG['apiKey']})
                requests.delete(f"{FIRESTORE_BASE}/shortlinks/{key}", params={"key": FIREBASE_CONFIG['apiKey']})
            except: pass
        self.root.after(0, self.refresh)

    def on_create(self):
        try:
            count = int(self.count_var.get())
            seconds = int(self.time_var.get())
        except: return

        self.create_btn.config(state='disabled')
        self.set_status(f'Đang khởi tạo {count} key...')
        threading.Thread(target=self._create_thread, args=(count, self.prefix_var.get(), seconds, bool(self.quote_var.get()), bool(self.auto_resolve_var.get())), daemon=True).start()

    def _create_thread(self, count, prefix, seconds, use_quote, auto_resolve):
        def progress_cb(current, total, link):
            self.root.after(0, self.set_status, f"Đang tạo {current}/{total}: {link}")

        try:
            generate_keys_logic(count, prefix, use_quote, auto_resolve, seconds, callback_progress=progress_cb)
            self.root.after(0, self._create_done)
        except Exception as e:
            self.root.after(0, messagebox.showerror, 'Lỗi', str(e))
            self.root.after(0, self.create_btn.config, {'state': 'normal'})

    def _create_done(self):
        messagebox.showinfo('Thành công', 'Đã tạo xong!')
        self.create_btn.config(state='normal')
        self.refresh()

    def on_export(self):
        rows = self.tree.get_children()
        links = [self.tree.item(r)['values'][1] for r in rows]
        try:
            with open('short.txt', 'w', encoding='utf-8') as f:
                f.write('\n'.join(links))
            messagebox.showinfo('OK', f'Đã xuất {len(links)} link.')
        except Exception as e:
            messagebox.showerror('Lỗi', str(e))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--count', '-n', type=int, default=1)
    parser.add_argument('--prefix', '-p', type=str, default='KEY_')
    
    # --- CẬP NHẬT: DEFAULT 300 GIÂY ---
    parser.add_argument('--time', '-t', type=int, default=300) 
    
    parser.add_argument('--no-resolve', action='store_true')
    parser.add_argument('--quote', action='store_true')
    parser.add_argument('--gui', action='store_true')
    parser.add_argument('--interactive', '-i', action='store_true', help='Chế độ tương tác: nhập số lượng và thời gian khi chạy CLI')
    args = parser.parse_args()

    if args.gui:
        root = tk.Tk()
        AdminGUI(root)
        root.mainloop()
    else:
        # CLI / Interactive Mode
        if args.interactive:
            try:
                print('--- INTERACTIVE MODE: Nhập các thông số (Enter để dùng mặc định giữa ngoặc) ---')
                cnt_raw = input(f'Số lượng [{args.count}]: ').strip()
                cnt = int(cnt_raw) if cnt_raw else args.count

                time_raw = input(f'Hết hạn (giây) [{args.time}]: ').strip()
                tsec = int(time_raw) if time_raw else args.time

                prefix_raw = input(f'Tiền tố [{args.prefix}]: ').strip()
                prefix = prefix_raw if prefix_raw else args.prefix

                araw = input(f'Auto Resolve? (Y/n) [{"Y" if not args.no_resolve else "n"}]: ').strip().lower()
                auto_resolve = False if araw == 'n' else True

                qraw = input(f'Url Encode? (y/N) [{"Y" if args.quote else "n"}]: ').strip().lower()
                quote_flag = True if qraw == 'y' else bool(args.quote)
            except Exception as e:
                print('Giá trị nhập không hợp lệ:', e)
                sys.exit(1)

            print(f"--- Đang tạo {cnt} key (Time: {tsec}s) Prefix: {prefix} ---")
            generate_keys_logic(
                count=cnt,
                prefix=prefix,
                use_quote=quote_flag,
                auto_resolve=auto_resolve,
                expires_seconds=tsec,
                callback_progress=lambda c, t, l: print(f"[{c}/{t}] {l}")
            )
        else:
            # Non-interactive CLI
            print(f"--- Đang tạo {args.count} key (Time: {args.time}s) ---")
            generate_keys_logic(
                count=args.count, 
                prefix=args.prefix, 
                use_quote=args.quote, 
                auto_resolve=not args.no_resolve,
                expires_seconds=args.time,
                callback_progress=lambda c, t, l: print(f"[{c}/{t}] {l}")
            )

if __name__ == '__main__':
    main()