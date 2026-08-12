# Use Case

## 1. Use Case ID và Tên use case

**UC-001 — Chạy Rolling Simulation và Xuất Dashboard KPI**

## 2. Mô tả ngắn (mục tiêu)

Cho phép actor kích hoạt một lượt mô phỏng nhiều chu kỳ liên tiếp (mặc định 12 tuần), chạy đầy đủ pipeline dự báo nhu cầu → tính safety stock/reorder point → tối ưu kế hoạch chuyển hàng có ràng buộc vận hành → giả lập bán hàng thực tế → cập nhật tồn kho → đo KPI, cho cả kịch bản baseline (không tối ưu) và kịch bản tối ưu, sau đó xuất kết quả ra một dashboard HTML tĩnh dùng để trình bày portfolio/CV.

## 3. Actor chính (và actor phụ nếu có)

- **Actor chính:** Portfolio Owner (người vận hành hệ thống — kiêm BA/dev theo BRD).
- **Actor phụ:** Không có. Hệ thống chạy offline/batch, không tích hợp actor hệ thống ngoài (đúng theo ràng buộc "không tích hợp hệ thống thật" — BR-024).

## 4. Stakeholders & mối quan tâm

| Stakeholder | Mối quan tâm |
|---|---|
| Portfolio Owner | Simulation chạy đúng logic, không lỗi giữa chừng; kết quả phản ánh trung thực giá trị hệ thống mang lại |
| Nhà tuyển dụng / Người xem CV | Dashboard trực quan, dễ hiểu, thể hiện rõ số liệu "trước/sau" (baseline vs tối ưu) |

## 5. Tiền điều kiện (Preconditions)

- Dữ liệu synthetic ban đầu (lịch sử bán hàng 52 tuần, danh mục sản phẩm, ma trận chi phí vận chuyển, lịch giao hàng cố định) đã được sinh sẵn theo quy mô ở Mục 7A.1 của BRD.
- Tham số cấu hình hệ thống (lead time, service level theo danh mục, sức chứa xe, ngưỡng cận hạn loại trừ) đã được thiết lập theo Mục 7A.2–7A.3 của BRD.
- Môi trường thực thi (Python 3.11+, statsmodels, pandas, NumPy, Plotly) đã cài đặt theo Mục 7A.4 của BRD.

## 6. Hậu điều kiện / Bảo đảm thành công (Postconditions)

- Hệ thống đã chạy đủ N chu kỳ tuần (mặc định 12) cho cả kịch bản baseline và kịch bản tối ưu.
- KPI theo tuần (stockout rate, excess inventory, chi phí vận chuyển, MAPE) đã được tính và lưu lại cho cả hai kịch bản.
- Một file dashboard HTML tĩnh, tự chứa (self-contained, không cần server), đã được xuất ra, hiển thị biểu đồ KPI theo tuần so sánh hai kịch bản.

## 7. Trigger

Actor khởi chạy lệnh/script chạy rolling simulation (ví dụ chạy entrypoint mô phỏng của hệ thống).

## 8. Luồng chính (Basic/Main flow)

1. Actor khởi chạy simulation, chỉ định số tuần mô phỏng (mặc định 12) và đường dẫn dữ liệu đầu vào.
2. Hệ thống nạp dữ liệu synthetic ban đầu và tham số cấu hình (Mục 7A của BRD).
3. Với mỗi tuần **t** từ 1 đến N, hệ thống thực hiện tuần tự cho **cả hai kịch bản** (baseline và tối ưu):
   1. Dự báo nhu cầu cho từng SKU/cửa hàng bằng Holt-Winters (BR-002); kịch bản baseline dùng trung bình 90 ngày (logic v1) làm mốc so sánh.
   2. Tính safety stock và reorder point theo service level/Z-score/lead time (BR-006, BR-007) — chỉ áp dụng cho kịch bản tối ưu.
   3. Xác định cửa hàng thừa/thiếu: theo reorder point/safety stock (BR-008) ở kịch bản tối ưu, theo days-of-inventory ở kịch bản baseline.
   4. Lập kế hoạch chuyển hàng bằng thuật toán được chọn (rule-based greedy hoặc genetic algorithm), tôn trọng ràng buộc sức chứa xe, lịch giao hàng cố định, FEFO và loại trừ hàng cận hạn (BR-010, BR-011, BR-013, BR-014, BR-015, BR-016) — bộ ràng buộc này chỉ áp dụng cho kịch bản tối ưu.
   5. Giả lập bán hàng thực tế của tuần **t** và cập nhật tồn kho tại từng cửa hàng.
   6. Tính và lưu KPI của tuần **t**: stockout rate, excess inventory, chi phí vận chuyển, MAPE (BR-019).
4. Sau khi hoàn tất N tuần, hệ thống tổng hợp chuỗi KPI theo tuần cho cả hai kịch bản.
5. Hệ thống dựng biểu đồ và xuất dashboard HTML tĩnh, tự chứa (BR-021).
6. Hệ thống thông báo hoàn tất và đường dẫn file dashboard cho actor.

## 9. Luồng thay thế (Alternate flows)

- **AF-1** (tại bước 1): Actor chỉ định số tuần khác 12 (ví dụ 4 tuần để kiểm thử nhanh) → hệ thống dùng giá trị đó thay cho mặc định, các bước còn lại không đổi.
- **AF-2** (tại bước 3.4): Actor chọn chỉ chạy một thuật toán (rule-based **hoặc** genetic algorithm) thay vì cả hai → hệ thống bỏ qua thuật toán còn lại trong toàn bộ simulation, dashboard chỉ hiển thị kết quả của thuật toán được chọn.

## 10. Luồng ngoại lệ / lỗi (Exception flows)

- **EF-1** (tại bước 2): Dữ liệu đầu vào thiếu file hoặc sai định dạng → hệ thống dừng, ghi log lỗi cụ thể, không tạo dashboard một phần.
- **EF-2** (tại bước 3.4): Không tìm được kế hoạch chuyển hàng nào thỏa toàn bộ ràng buộc cứng trong tuần đó (ví dụ không có tuyến giao hàng hợp lệ) → hệ thống ghi nhận "không chuyển hàng tuần t", tiếp tục sang tuần kế tiếp thay vì dừng toàn bộ simulation.
- **EF-3** (tại bước 5): Lỗi khi dựng biểu đồ/xuất HTML → hệ thống vẫn giữ lại dữ liệu KPI thô đã tính được, báo lỗi cụ thể tại bước xuất dashboard, không làm mất kết quả simulation đã chạy.

## 11. Business rules liên quan

BR-002, BR-006, BR-007, BR-008, BR-010, BR-011, BR-013, BR-014, BR-015, BR-016, BR-017, BR-018, BR-019, BR-020, BR-021 — nguồn: `inventory-transfer-optimization-v2-BRD.md`.

## 12. Yêu cầu phi chức năng liên quan

- Kết quả simulation phải tái lập được khi dùng cùng random seed (theo Mục 10 — Dependencies của BRD).
- Thời gian chạy tối đa chấp nhận được cho một lượt simulation đầy đủ (12 tuần, cả hai thuật toán, cả hai kịch bản): dưới 15 phút trên máy cá nhân thông thường (laptop dev, không có GPU) — ngưỡng mềm cho mục đích demo, không phải SLA cứng (giải quyết OQ-007).

## 13. Tần suất / Giả định / Câu hỏi mở

**Tần suất:** Chạy theo yêu cầu (on-demand) mỗi khi actor cần tạo hoặc tái tạo bản demo — không phải tác vụ định kỳ tự động.

**Giả định:**
- Dữ liệu synthetic ban đầu đã tồn tại sẵn trước khi use case này bắt đầu (là tiền điều kiện, không thuộc phạm vi use case này).

**Câu hỏi mở:**
- [x] OQ-007: Ngưỡng thời gian chạy — **Đã giải quyết**: xem Mục 12 (NFR) ở trên.
- [x] OQ-008: Quy trình sinh dữ liệu synthetic ban đầu chưa có use case riêng — **Đã giải quyết**: bổ sung UC-003 — Sinh dữ liệu Synthetic Ban đầu (xem `synthetic-data-generation-use-case.md`).
