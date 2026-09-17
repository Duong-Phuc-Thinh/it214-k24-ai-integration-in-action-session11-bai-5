# Tích hợp WebClient & Kafka - Xử lý luồng sự kiện thông báo thông minh

## Giới thiệu
Bài toán mô phỏng hệ thống xử lý sự kiện bất đồng bộ bằng Python (giả lập Spring WebClient và Kafka Consumer với tính năng Idempotency, Retry, Fallback và Dead Letter Queue).

## Các chức năng đã làm
- Lắng nghe sự kiện từ Kafka topic `storex-order-events`.
- Kiểm tra tính lũy đẳng (Idempotency) để tránh xử lý trùng lặp `orderId`.
- Gọi API lấy thông tin ưu đãi người dùng với cơ chế Retry, Timeout và Fallback sang EMAIL nếu lỗi.
- Gửi thông báo qua kênh tương ứng và đẩy vào DLQ (`storex-order-events.DLQ`) nếu thất bại hoàn toàn.

## Hướng dẫn chạy
```bash
python main.py
```