"""Polite fallback messages — VI/EN.

KHÔNG hardcode polite strings inline ở engine/API; import từ đây.
"""

from __future__ import annotations

POLITE_FALLBACK: dict[str, str] = {
    "vi": (
        "Xin lỗi, tôi chưa thể trả lời câu hỏi này lúc này. "
        "Vui lòng thử lại sau hoặc liên hệ admin nếu vấn đề tiếp diễn."
    ),
    "en": (
        "Sorry, I'm unable to answer this question right now. "
        "Please try again later or contact admin if the issue persists."
    ),
}

NO_CONTEXT: dict[str, str] = {
    "vi": (
        "Xin lỗi, tôi chưa có đủ thông tin để trả lời câu hỏi này. "
        "Bạn có thể cung cấp thêm chi tiết hoặc liên hệ admin."
    ),
    "en": (
        "Sorry, I don't have enough information to answer this question. "
        "Please provide more details or contact admin."
    ),
}

POLITE_REFUSAL: dict[str, str] = {
    "vi": (
        "Xin lỗi, tôi không thể xử lý yêu cầu này. "
        "Vui lòng đặt câu hỏi liên quan đến tài liệu nội bộ."
    ),
    "en": (
        "Sorry, I cannot process this request. "
        "Please ask a question related to internal documents."
    ),
}
