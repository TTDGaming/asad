# Asad · App quản lý dịch phim & tải video

Web app dạng PWA, chạy được trên **Windows** (trình duyệt / cài như app
desktop qua Chrome/Edge) và **iPhone** (Safari → *Add to Home Screen* sẽ
thành biểu tượng như app native).

Có sẵn khung để thêm **Douyin (抖音)** và **Hongguo (红果短剧)** — bạn chỉ
cần dán logic API vào hai file `backend/downloaders/douyin.py` và
`backend/downloaders/hongguo.py` khi có key.

---

## Tính năng

| Nhóm | Mô tả |
|---|---|
| Dự án | Tạo dự án cho từng phim/tập, ghi ngôn ngữ gốc → đích, provider, URL nguồn. |
| Dịch | Thêm dòng phụ đề có timestamp, trạng thái (draft / in_progress / reviewing / completed). Xuất file `.srt`. |
| Tải xuống | Hàng đợi chạy nền; tiến độ cập nhật realtime; hỗ trợ cancel / retry / xóa. |
| Lưu trực tiếp | Nút **"Lưu về máy"** trả file video — trên iPhone sẽ lưu vào *Files* / *Photos*, trên Windows là Downloads. |
| Provider mở rộng | Plugin system: thêm downloader mới = thêm 1 file Python. |

---

## Chạy ở local

```bash
pip install -r requirements.txt
python run.py
```

Mặc định nghe ở `0.0.0.0:8000`.

- **Windows**: mở <http://localhost:8000>. Chrome/Edge có nút *Install app* trên thanh địa chỉ.
- **iPhone** (cùng WiFi với máy chạy server): mở Safari tới
  `http://<IP-máy>:8000` → nút *Share* → *Add to Home Screen*.

---

## Thêm provider (ví dụ Douyin)

File `backend/downloaders/douyin.py`:

```python
@registry.register("douyin")
class DouyinDownloader(BaseDownloader):
    name = "Douyin (抖音)"
    enabled = True  # ← bật lên khi xong

    @classmethod
    def matches(cls, url: str) -> bool:
        return "douyin.com" in url

    async def download(self, ctx, on_progress):
        # 1. Gọi API của bạn để resolve URL share → direct media URL
        direct_url = await resolve_douyin(ctx.url)  # logic của bạn

        # 2. Dùng lại GenericHttpDownloader để stream file
        from .generic import GenericHttpDownloader
        inner_ctx = DownloadContext(
            url=direct_url,
            output_dir=ctx.output_dir,
            filename_hint="douyin",
        )
        return await GenericHttpDownloader().download(inner_ctx, on_progress)
```

Không cần sửa chỗ khác — tab **Nguồn** trong UI sẽ tự nhận và cho chọn.

---

## Cấu trúc

```
backend/
  main.py               # FastAPI app + static mount frontend
  database.py           # SQLAlchemy engine + session
  models.py             # Project / Download / Translation
  schemas.py            # Pydantic schemas
  download_manager.py   # Worker async xử lý hàng chờ
  downloaders/
    base.py             # BaseDownloader + registry
    generic.py          # Tải URL HTTP trực tiếp
    douyin.py           # ← bạn sẽ bổ sung API
    hongguo.py          # ← bạn sẽ bổ sung API
  routers/
    projects.py
    translations.py     # + xuất .srt
    downloads.py        # + /providers, /{id}/file
frontend/
  index.html
  style.css
  app.js
  manifest.json         # PWA
  sw.js                 # Service worker cache shell
  icons/                # 192 & 512
storage/                # DB sqlite + video tải về (đã .gitignore)
run.py
requirements.txt
```

---

## API tóm tắt

- `GET  /api/projects` · `POST /api/projects` · `PATCH /api/projects/{id}` · `DELETE /api/projects/{id}`
- `GET  /api/translations?project_id=…` · `POST /api/translations` · `PATCH/DELETE /api/translations/{id}`
- `GET  /api/translations/export/srt?project_id=…`
- `GET  /api/downloads/providers`
- `POST /api/downloads` *(body: `{project_id, url, provider?}`)*
- `POST /api/downloads/{id}/cancel` · `POST /api/downloads/{id}/retry`
- `GET  /api/downloads/{id}/file` *(trả file video để lưu trực tiếp)*

Khám phá schema đầy đủ ở `/docs` (Swagger UI).
