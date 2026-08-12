"""BR-025, BR-026 — đặt hàng bổ sung từ nhà cung cấp khi chạm ngưỡng reorder (order-up-to policy)."""


def compute_replenishment_order(current_stock: float, reorder_threshold: float, target_level: float) -> float:
    if current_stock >= reorder_threshold:
        return 0.0
    return max(0.0, target_level - current_stock)
