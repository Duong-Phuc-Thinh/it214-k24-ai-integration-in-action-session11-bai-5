import time
import logging
from concurrent.futures import ThreadPoolExecutor

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class IdempotencyManager:
    def __init__(self):
        self.processed_orders = set()

    def is_processed(self, order_id):
        return order_id in self.processed_orders

    def mark_processed(self, order_id):
        self.processed_orders.add(order_id)

class MockWebClient:
    @staticmethod
    def get_preference(user_id):
        # Giả lập lỗi API hoặc Timeout
        if user_id == "user_error":
            raise ConnectionError("User Preference API connection refused")
        return "ZALO" if user_id == "user_zalo" else "EMAIL"

    @staticmethod
    def send_notification(channel, order_id):
        if order_id == "ORD-FAIL":
            raise RuntimeError("Notification API failed")
        logger.info(f"Đã gửi thông báo thành công qua kênh {channel} cho đơn hàng {order_id}")
        return True

class NotificationConsumer:
    def __init__(self):
        self.idempotency_manager = IdempotencyManager()
        self.dlq = []

    def process_message(self, message):
        order_id = message.get("orderId")
        user_id = message.get("userId")

        # 1. Kiểm tra tính lũy đẳng (BUG-06)
        if self.idempotency_manager.is_processed(order_id):
            logger.info(f"Message với orderId = {order_id} đã được xử lý trước đó. Bỏ qua.")
            return

        # 2. Gọi User Preference API với Fallback (BUG-05)
        channel = "EMAIL"  # Mặc định Fallback
        try:
            channel = MockWebClient.get_preference(user_id)
        except Exception as e:
            logger.warning(f"Lỗi khi gọi Preference API: {e}. Chuyển sang Fallback kênh EMAIL.")

        # 3. Gửi thông báo với Retry (Tối đa 2 lần)
        success = False
        retries = 2
        for attempt in range(retries + 1):
            try:
                MockWebClient.send_notification(channel, order_id)
                success = True
                break
            except Exception as e:
                logger.warning(f"Lần thử {attempt + 1} gửi thông báo thất bại cho {order_id}: {e}")
                if attempt < retries:
                    time.sleep(1)

        # 4. Xử lý DLQ nếu thất bại hoàn toàn (BUG-07)
        if not success:
            logger.error(f"Đã đẩy order {order_id} vào DLQ do lỗi gửi thông báo")
            self.dlq.append(message)
        else:
            # Đánh dấu đã xử lý thành công
            self.idempotency_manager.mark_processed(order_id)

if __name__ == "__main__":
    consumer = NotificationConsumer()

    # Test các kịch bản
    messages = [
        {"orderId": "ORD-123", "userId": "user_zalo"},
        {"orderId": "ORD-123", "userId": "user_zalo"},  # Trùng lặp (Idempotency)
        {"orderId": "ORD-456", "userId": "user_error"}, # Lỗi Preference API -> Fallback
        {"orderId": "ORD-FAIL", "userId": "user_email"} # Lỗi gửi thông báo -> DLQ
    ];

    for msg in messages:
        logger.info(f"Nhận message: {msg}")
        consumer.process_message(msg)
        print("-" * 40)
