# Use Case

## 1. Use Case ID và Tên use case

**UC-003 — Sinh Dữ liệu Synthetic Ban đầu**

## 2. Mô tả ngắn (mục tiêu)

Cho phép Portfolio Owner kích hoạt script sinh toàn bộ dữ liệu synthetic ban đầu cho hệ thống: lịch sử bán hàng 52 tuần có seasonality/trend/promotion cho từng SKU/cửa hàng (BR-001), thuộc tính sản phẩm theo danh mục — lead time (BR-004), service level mục tiêu (BR-005), thể tích/trọng lượng (BR-009), và thuộc tính lô hàng tồn kho — hạn sử dụng theo batch (BR-012) — theo đúng quy mô và tham số cấu hình ở Mục 7A của BRD. Đây là use case giải quyết OQ-008 của [UC-001](UC-001-rolling-simulation-dashboard.md) và là **tiền điều kiện bắt buộc** trước khi UC-001 có thể chạy.

## 3. Actor chính (và actor phụ nếu có)

- **Actor chính:** Portfolio Owner (người vận hành, kích hoạt script sinh dữ liệu).
- **Actor phụ:** Không có. Hệ thống chạy offline/batch, không tích hợp actor hệ thống ngoài (đúng theo ràng buộc "không tích hợp hệ thống thật" — BR-024).

## 4. Stakeholders & mối quan tâm

| Stakeholder | Mối quan tâm |
|---|---|
| Portfolio Owner | Dữ liệu sinh ra đủ chân thực (seasonality/trend/promotion rõ ràng) để dự báo và simulation có ý nghĩa minh họa; tái lập được giữa các lần chạy |
| UC-001 (Rolling Simulation) | Nhận đủ và đúng định dạng toàn bộ dữ liệu đầu vào cần thiết (Mục 5 — Tiền điều kiện của UC-001) để chạy không lỗi |

## 5. Tiền điều kiện (Preconditions)

- Môi trường thực thi (Python 3.11+, pandas, NumPy) đã cài đặt theo Mục 7A.4 của BRD.
- Tham số quy mô dữ liệu (Mục 7A.1), ràng buộc vận hành (Mục 7A.2), và service level theo danh mục (Mục 7A.3) đã được xác định trong script/cấu hình generator.
- Random seed sinh dữ liệu đã được xác định, để đảm bảo khả năng tái lập (Mục 10 — Dependencies của BRD).

## 6. Hậu điều kiện / Bảo đảm thành công (Postconditions)

- Bộ dữ liệu synthetic ban đầu đầy đủ (lịch sử bán hàng, thuộc tính sản phẩm, thuộc tính lô hàng tồn kho, ma trận chi phí vận chuyển, lịch giao hàng cố định) đã được sinh ra và lưu lại.
- Dữ liệu thỏa mãn đúng tiền điều kiện của UC-001 (Mục 5 của UC-001) — sẵn sàng để UC-001 nạp và chạy mà không cần bước chuẩn bị dữ liệu nào thêm.
- OQ-008 của UC-001 ("quy trình sinh dữ liệu synthetic chưa được tài liệu hóa thành use case riêng") được giải quyết bằng chính use case này.

## 7. Trigger

Actor khởi chạy lệnh/script sinh dữ liệu synthetic (entrypoint data generator), thường thực hiện trước lần đầu chạy UC-001, hoặc khi actor muốn tái tạo một bộ dữ liệu demo mới (ví dụ đổi seed).

## 8. Luồng chính (Basic/Main flow)

1. Actor khởi chạy script sinh dữ liệu, có thể chỉ định random seed và đường dẫn output.
2. Hệ thống nạp tham số quy mô theo Mục 7A.1: 20 cửa hàng/3 thành phố, 30 SKU/5 danh mục, 52 tuần lịch sử.
3. Hệ thống sinh danh mục cửa hàng (20 cửa hàng, phân bổ theo 3 thành phố: Hà Nội, TP.HCM, Đà Nẵng).
4. Hệ thống sinh danh mục sản phẩm (30 SKU), gán mỗi SKU vào một trong 5 danh mục hàng, và gán thuộc tính theo danh mục: lead time (BR-004), service level mục tiêu và Z-score tương ứng (BR-005 — giá trị cụ thể tại Mục 7A.3), thể tích/trọng lượng đơn vị (BR-009).
5. Hệ thống sinh chuỗi lịch sử bán hàng 52 tuần (364 ngày) cho từng cặp SKU/cửa hàng, có thành phần seasonality (mùa vụ theo tuần), trend (xu hướng), và hiệu ứng promotion (khuyến mãi) rõ ràng, có thể kiểm chứng bằng phân rã chuỗi thời gian (BR-001).
6. Hệ thống sinh dữ liệu tồn kho ban đầu theo lô hàng (batch) cho từng SKU/cửa hàng, kèm thuộc tính hạn sử dụng (expiry date) ở cấp lô hàng (BR-012).
7. Hệ thống sinh ma trận chi phí vận chuyển giữa các cặp cửa hàng và lịch giao hàng cố định (2 ngày/tuần/tuyến, sinh ngẫu nhiên nhưng cố định theo seed cho từng tuyến — Mục 7A.2).
8. Hệ thống lưu toàn bộ dữ liệu synthetic đã sinh vào đường dẫn output đã chỉ định.
9. Hệ thống thông báo hoàn tất và in ra đường dẫn/tóm tắt dữ liệu đã sinh cho actor.

## 9. Luồng thay thế (Alternate flows)

- **AF-1** (tại bước 1): Actor chỉ định seed khác mặc định để sinh một bộ dữ liệu demo khác → toàn bộ luồng dùng seed đó; kết quả khác về giá trị nhưng vẫn tái lập được nếu dùng lại đúng seed.
- **AF-2** (tại bước 2): Actor chỉ định quy mô khác Mục 7A.1 (ví dụ ít cửa hàng/SKU hơn) để tạo bộ dữ liệu nhỏ phục vụ kiểm thử nhanh → hệ thống dùng quy mô đó thay cho mặc định, các bước còn lại không đổi.
- **AF-3** (sau bước 9): Actor review trực quan (plot) dữ liệu vừa sinh theo khuyến nghị giảm thiểu rủi ro tại Mục 11 của BRD ("dữ liệu synthetic không đủ chân thực") → nếu seasonality/trend/promotion chưa đủ rõ ràng, actor điều chỉnh tham số generator và lặp lại từ bước 1; danh sách tham số cụ thể có thể điều chỉnh chưa được BRD liệt kê chi tiết (xem OQ-012).

## 10. Luồng ngoại lệ / lỗi (Exception flows)

- **EF-1** (tại bước 8): Lỗi khi ghi file output (ví dụ không đủ quyền ghi hoặc hết dung lượng đĩa) → hệ thống dừng, báo lỗi cụ thể, không để lại bộ dữ liệu ghi dở/không toàn vẹn (không tạo dữ liệu bán phần).

## 11. Business rules liên quan

BR-001, BR-004, BR-005, BR-009, BR-012 — nguồn: `inventory-transfer-optimization-v2-BRD.md`, tham số cụ thể tại Mục 7A.1–7A.3.

## 12. Yêu cầu phi chức năng liên quan

- Dữ liệu sinh ra phải tái lập được (reproducible) khi dùng cùng random seed (Mục 10 — Dependencies của BRD).
- Thời gian chạy tối đa chấp nhận được cho một lượt sinh dữ liệu đầy đủ: dưới 2 phút trên máy cá nhân thông thường — nhẹ hơn nhiều so với ngưỡng simulation (Mục 12 của UC-001) vì đây chỉ là sinh dữ liệu, không chạy forecasting/optimization (giải quyết OQ-013).

## 13. Tần suất / Giả định / Câu hỏi mở

**Tần suất:** Chạy theo yêu cầu (on-demand) — một lần trước khi bắt đầu sử dụng hệ thống, hoặc bất cứ khi nào actor muốn tái tạo một bộ dữ liệu demo mới (ví dụ đổi seed cho lần trình bày khác); không phải tác vụ định kỳ tự động.

**Giả định:**
- Bộ dữ liệu sinh ra một lần đủ dùng cho nhiều lượt chạy UC-001 liên tiếp — không cần sinh lại dữ liệu mỗi khi chạy UC-001, trừ khi actor chủ động muốn tái tạo bộ dữ liệu khác.

**Câu hỏi mở:**
- [x] OQ-011: Định dạng lưu trữ output — **Đã giải quyết**: CSV, giữ cấu trúc thư mục `data/` kế thừa quy ước v1: `stores.csv`, `products.csv` (mở rộng thêm cột lead_time_days, service_level, z_score, weight_kg, volume_l), `sales_data.csv` (52 tuần, mở rộng thêm cột is_promotion), `inventory_batches.csv` (thay `inventory_data.csv` cũ, thêm batch_id, expiry_date), `distance_matrix.csv`, `transport_cost_matrix.csv` (giữ như v1), `delivery_schedule.csv` (mới: cặp cửa hàng, ngày giao cố định). Lý do: nhất quán với v1, dễ đọc/diff trong git, đủ nhẹ cho quy mô dữ liệu ở Mục 7A.1 — không cần Parquet/SQLite.
- [x] OQ-012: Tham số generator có thể điều chỉnh — **Đã giải quyết**: biên độ seasonality (% dao động theo tuần so với baseline), độ dốc trend (% tăng/giảm mỗi tuần), tần suất promotion (số đợt/năm) và mức uplift promotion (% tăng doanh số trong đợt), độ nhiễu ngẫu nhiên (variance quanh giá trị kỳ vọng) — đưa vào một config (dataclass/dict) trong generator script, có giá trị mặc định tạo pattern rõ ràng để dự báo có ý nghĩa minh họa.
- [x] OQ-013: Ngưỡng thời gian chạy — **Đã giải quyết**: xem Mục 12 (NFR) ở trên.
