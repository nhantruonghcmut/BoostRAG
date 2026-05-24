"""Business logic layer.

Stateless functions/classes. Nhận `AsyncSession` qua DI, return domain
objects hoặc raise `AppError` subclass. KHÔNG nhận Request/Response object
(để tái sử dụng được trong CLI/worker).
"""
